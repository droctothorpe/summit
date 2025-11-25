"""Sched.com scraping and processing utilities for Summit."""

import asyncio
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .core import get_cache_dir, process_video
from .summarizers import Summarizer, get_summarizer


def _safe_filename_from_url(url: str) -> str:
    """Create a filesystem-safe filename based on a URL."""
    parsed = urlparse(url)
    # Use scheme, netloc, path and query so different event URLs map to different files
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        base += f"?{parsed.query}"
    # Replace any characters that are not safe for filenames
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe


def get_sched_cache_path(sched_url: str):
    """Get the cache file path for a sched.com URL."""
    filename = _safe_filename_from_url(sched_url)
    return get_cache_dir() / f"sched_{filename}.json"


def load_sched_cache(sched_url: str) -> Optional[List[Dict]]:
    """Load cached sched talks if available."""
    cache_path = get_sched_cache_path(sched_url)
    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                print(f"Using cached sched data from {cache_path}")
                return data
        except Exception as e:
            print(f"Error loading sched cache: {e}")
            return None
    return None


def save_sched_cache(sched_url: str, talks: List[Dict]) -> None:
    """Save sched talks to cache."""
    cache_path = get_sched_cache_path(sched_url)
    try:
        with open(cache_path, "w") as f:
            json.dump(talks, f, indent=2)
        print(f"Cached sched data to {cache_path}")
    except Exception as e:
        print(f"Error saving sched cache: {e}")


async def _fetch_talk_detail(sched_link: str) -> Optional[Dict]:
    """Fetch a single talk's detail page to extract title, description, and YouTube link."""
    try:
        loop = asyncio.get_event_loop()

        # In case Sched renders parts of the page slowly, retry a few times
        max_attempts = 3
        detail_soup = None
        title_elem = None

        for attempt in range(1, max_attempts + 1):
            # Run requests.get in thread pool to avoid blocking
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(sched_link, timeout=15)
            )

            detail_soup = BeautifulSoup(response.text, 'html.parser')
            title_elem = detail_soup.find(class_='name')

            if title_elem:
                break

            if attempt < max_attempts:
                # Wait briefly before retrying to give the page a chance to fully render
                await asyncio.sleep(1.0)

        if not title_elem:
            print(f"Could not find title element with class 'name' in {sched_link} after {max_attempts} attempts")
            return None

        # The full title includes both talk title and speakers
        title = title_elem.get_text(strip=True)

        print(f"Fetching detail page for: {title}")

        # Extract description from element with class "tip-description" if present
        description_elem = detail_soup.find(class_='tip-description')
        description = description_elem.get_text(strip=True) if description_elem else ""

        # Extract event type from element with class "sched-event-type" if present
        event_type_elem = detail_soup.find(class_='sched-event-type')
        if event_type_elem:
            # The event type is in the FIRST direct child <a> of this div
            # (there may also be an unordered list with extra links we should ignore).
            first_anchor = None
            for child in event_type_elem.children:
                if getattr(child, 'name', None) == 'a':
                    first_anchor = child
                    break

            if first_anchor is not None:
                text = first_anchor.get_text(strip=True)
                event_type = text if text else None
            else:
                event_type = None
        else:
            event_type = None
        
        # Look for YouTube links in detail page
        youtube_links = detail_soup.find_all('a', href=re.compile(r'youtube\.com/watch|youtu\.be/'))
        youtube_url = None
        
        if youtube_links:
            youtube_url = youtube_links[0].get('href')
        
        # Also check for embedded YouTube iframes
        if not youtube_url:
            youtube_iframes = detail_soup.find_all('iframe', src=re.compile(r'youtube\.com/embed/'))
            if youtube_iframes:
                iframe_src = youtube_iframes[0].get('src')
                # Extract video ID from embed URL and construct watch URL
                video_id_match = re.search(r'youtube\.com/embed/([^?&/]+)', iframe_src)
                if video_id_match:
                    youtube_url = f"https://www.youtube.com/watch?v={video_id_match.group(1)}"
        
        # Look for an attached deck in div.sched-file (first anchor)
        deck_url = None
        deck_container = detail_soup.find('div', class_='sched-file')
        if deck_container:
            deck_anchor = deck_container.find('a', href=True)
            if deck_anchor:
                href = deck_anchor['href']
                if href and not href.startswith('http'):
                    base_url = '/'.join(sched_link.split('/')[:3])
                    href = base_url + href
                deck_url = href

        if youtube_url:
            print(f"Found YouTube video for: {title}")
            return {
                'title': title,
                'sched_link': sched_link,
                'youtube_url': youtube_url,
                'description': description,
                'event_type': event_type,
                'deck_url': deck_url,
            }
        else:
            print(f"Skipping (no YouTube video): {title}")
            return None
            
    except Exception as e:
        print(f"Could not fetch detail page for {sched_link}: {e}")
        return None


async def scrape_sched_talks_async(sched_url: str, limit: Optional[int] = None, sleep: int = 0, offset: int = 0) -> List[Dict]:
    """Scrape talks from a sched.com event page (async version).

    The offset parameter controls how many initial schedule entries are skipped
    **without** fetching their detail pages, to avoid unnecessary requests
    when the user only cares about talks after a certain point.
    """
    # Ensure URL has /list/descriptions path
    if '/list/descriptions' not in sched_url:
        # Parse the URL and add the path
        parsed = urlparse(sched_url)
        # Reconstruct with /list/descriptions
        sched_url = f"{parsed.scheme}://{parsed.netloc}/list/descriptions"
    
    print(f"Scraping talks from {sched_url}...")
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(sched_url, timeout=30)
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching sched.com page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all event items - sched.com uses various class names, we'll try common patterns
    # Look for event containers
    event_items = soup.find_all('div', class_=re.compile(r'sched-container-inner|event-container'))
    
    if not event_items:
        # Try alternative structure - look for links with event info
        event_items = soup.find_all('a', href=re.compile(r'/event/'))
    
    if not event_items:
        # Try even broader search - any div with event-related classes
        event_items = soup.find_all('div', class_=re.compile(r'event|session|talk'))
    
    print(f"Found {len(event_items)} potential event items to parse")
    
    # Extract sched links from all items first
    sched_links = []
    for item in event_items:
        try:
            # Extract sched link
            link_elem = item.find('a', href=re.compile(r'/event/'))
            if not link_elem:
                continue
            
            sched_link = link_elem.get('href')
            if not sched_link.startswith('http'):
                # Make absolute URL
                base_url = '/'.join(sched_url.split('/')[:3])
                sched_link = base_url + sched_link
            
            sched_links.append(sched_link)
        except Exception as e:
            print(f"Error parsing event item: {e}")
            continue
    
    # Fetch detail pages sequentially to better control request rate
    print(f"Fetching detail pages for {len(sched_links)} talks...")
    talks: List[Dict] = []
    current_offset = offset if offset and offset > 0 else 0

    for idx, link in enumerate(sched_links, start=1):
        # If an offset is specified, skip issuing detail requests for the
        # first N schedule entries entirely.
        if current_offset > 0:
            current_offset -= 1
            continue

        talk = await _fetch_talk_detail(link)
        if talk is not None:
            talks.append(talk)

        # Apply limit early if we've collected enough talks with YouTube videos
        if limit and len(talks) >= limit:
            break

        # Sleep between requests if configured
        if sleep and sleep > 0:
            await asyncio.sleep(sleep)

    if limit and len(talks) > limit:
        talks = talks[:limit]
        print(f"Limited to {limit} talks with YouTube videos")

    print(f"Found {len(talks)} talks with YouTube videos")
    return talks


def scrape_sched_talks(sched_url: str, limit: Optional[int] = None, sleep: int = 0, offset: int = 0) -> List[Dict]:
    """Scrape talks from a sched.com event page (sync wrapper)."""
    return asyncio.run(scrape_sched_talks_async(sched_url, limit, sleep, offset))


async def process_sched_talks(sched_url: str, summarizer: Optional[Summarizer] = None, limit: Optional[int] = None, refresh_cache: bool = False, summarize: bool = True, offset: int = 0, sleep: int = 0, use_summary_cache: bool = True, proxy: bool = False) -> Dict[str, Dict]:
    """Process talks from a sched.com event page."""
    print(f"Processing sched.com event: {sched_url}")
    
    # Use default summarizer if none provided and summarization is enabled
    if summarizer is None and summarize:
        summarizer = get_summarizer("anthropic")
    
    talks = None
    used_cache = False
    # Try to load cached talks first unless refresh is requested
    if not refresh_cache:
        talks = load_sched_cache(sched_url)
        if talks is not None:
            print(f"Loaded {len(talks)} talks from cache")
            used_cache = True
    
    if talks is None:
        # Cache miss or refresh requested - scrape talks from sched.com.
        # Use offset at the scraping layer to avoid fetching skipped detail pages.
        # Limit still controls how many talks with YouTube videos we collect.
        fetch_limit: Optional[int] = None
        if limit is not None and limit > 0:
            fetch_limit = limit

        talks = await scrape_sched_talks_async(sched_url, limit=fetch_limit, sleep=sleep, offset=offset)

        # Save to cache only when we are not using an offset, so the cache
        # always represents the full un-offset set of talks.
        if talks and not refresh_cache and offset == 0:
            save_sched_cache(sched_url, talks)
    
    if not talks:
        print("No talks with YouTube videos found")
        return {}

    original_count = len(talks)

    # Apply offset only when working from cache (cache always stores the
    # full un-offset set). When scraping in this run, offset has already
    # been applied at the sched-link level above.
    if used_cache and offset and offset > 0:
        talks = talks[offset:]
        print(f"Skipping first {offset} talks from cache, remaining {len(talks)} of {original_count}")

    # Then apply limit to the remaining talks
    if limit is not None and limit > 0 and len(talks) > limit:
        talks = talks[:limit]
        print(f"Applying limit {limit}, processing first {len(talks)} talks out of remaining set")

    # If summarization is disabled, return descriptions from Sched as summaries
    if not summarize:
        print(f"Building output from Sched descriptions for {len(talks)} talks...")
        output: Dict[str, Dict] = {}
        for idx, talk in enumerate(talks, start=1):
            youtube_url = talk['youtube_url']
            description = talk.get('description', "")
            event_type = talk.get('event_type') or ""
            deck_url = talk.get('deck_url') or ""
            result = {
                "index": idx,
                "title": talk['title'],
                "summary": description,
                "sched_link": talk['sched_link'],
            }
            if event_type:
                result["event_type"] = event_type
            if deck_url:
                result["deck_url"] = deck_url
            output[youtube_url] = result
        return output

    print(f"Processing {len(talks)} talks with summarization...")

    # Process talks asynchronously using the summarizer
    tasks = []
    for idx, talk in enumerate(talks, start=1):
        tasks.append(process_video(
            video_url=talk['youtube_url'],
            index=idx,
            title=talk['title'],
            summarizer=summarizer,
            speakers=None,  # Speakers are included in the title
            sched_link=talk['sched_link'],
            use_summary_cache=use_summary_cache,
            proxy=proxy,
            sleep=sleep,
        ))

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)

    # Build result dictionary
    output: Dict[str, Dict] = {}
    for idx, result in enumerate(results, start=1):
        if result:
            youtube_url = talks[idx - 1]['youtube_url']
            # Attach event_type to the result if present in scraped talks
            event_type = talks[idx - 1].get('event_type') or ""
            deck_url = talks[idx - 1].get('deck_url') or ""
            if event_type:
                result["event_type"] = event_type
            if deck_url:
                result["deck_url"] = deck_url
            output[youtube_url] = result

    return output
