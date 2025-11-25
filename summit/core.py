"""Core functionality for Summit library."""

import asyncio
import hashlib
import json
from logging import warning
import re
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

from .summarizers import Summarizer, get_summarizer


def get_cache_dir() -> Path:
    """Get or create the cache directory."""
    cache_dir = Path.home() / '.cache' / 'summit'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_playlist_cache_path(playlist_url: str) -> Path:
    """Get the cache file path for a playlist."""
    # Create a hash of the playlist URL to use as filename
    url_hash = hashlib.md5(playlist_url.encode()).hexdigest()
    return get_cache_dir() / f'playlist_{url_hash}.json'


def load_playlist_cache(playlist_url: str) -> Optional[List[Dict]]:
    """Load cached playlist data if it exists."""
    cache_path = get_playlist_cache_path(playlist_url)
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                print(f"Using cached playlist data from {cache_path}")
                return data
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None
    return None


def save_playlist_cache(playlist_url: str, videos: List[Dict]) -> None:
    """Save playlist data to cache."""
    cache_path = get_playlist_cache_path(playlist_url)
    try:
        with open(cache_path, 'w') as f:
            json.dump(videos, f, indent=2)
        print(f"Cached playlist data to {cache_path}")
    except Exception as e:
        print(f"Error saving cache: {e}")
def get_subtitle_cache_path(video_id: str) -> Path:
    """Get the cache file path for subtitles of a specific video."""
    subtitle_dir = Path.home() / '.cache' / 'subtitles'
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    return subtitle_dir / f"subtitles_{video_id}.txt"


def load_subtitle_cache(video_id: str) -> Optional[str]:
    """Load cached subtitles for a video if available."""
    cache_path = get_subtitle_cache_path(video_id)
    if cache_path.exists():
        try:
            text = cache_path.read_text(encoding="utf-8")
            print(f"Using cached subtitles for video {video_id} from {cache_path}")
            return text
        except Exception as e:
            print(f"Error loading subtitle cache for {video_id}: {e}")
            return None
    return None


def save_subtitle_cache(video_id: str, subtitles: str) -> None:
    """Save subtitles for a video to cache."""
    cache_path = get_subtitle_cache_path(video_id)
    try:
        cache_path.write_text(subtitles, encoding="utf-8")
        print(f"Cached subtitles for video {video_id} to {cache_path}")
    except Exception as e:
        print(f"Error saving subtitle cache for {video_id}: {e}")


def _summarizer_cache_key_parts(summarizer: Summarizer) -> str:
    """Build a stable identifier string for a summarizer instance for caching.

    We include the class name, model (if present), and summary_length (if present)
    so that switching models or target lengths results in separate cache files.
    """
    cls_name = summarizer.__class__.__name__
    model = getattr(summarizer, "model", None)
    summary_length = getattr(summarizer, "summary_length", None)

    parts = [cls_name]
    if model:
        parts.append(str(model))
    if summary_length:
        parts.append(str(summary_length))

    raw = "_".join(parts)
    # Make safe for filenames
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", raw)
    return safe


def get_summary_cache_path(video_id: str, summarizer: Summarizer) -> Path:
    """Get the cache file path for a summarized video for a given summarizer."""
    key = _summarizer_cache_key_parts(summarizer)
    summary_dir = get_cache_dir() / 'summaries'
    summary_dir.mkdir(parents=True, exist_ok=True)
    return summary_dir / f"summary_{video_id}_{key}.txt"


def load_summary_cache(video_id: str, summarizer: Summarizer) -> Optional[str]:
    """Load cached summary for a video/summarizer combo if available."""
    cache_path = get_summary_cache_path(video_id, summarizer)
    if cache_path.exists():
        try:
            text = cache_path.read_text(encoding="utf-8")
            print(f"Using cached summary for video {video_id} from {cache_path}")
            return text
        except Exception as e:
            print(f"Error loading summary cache for {video_id}: {e}")
            return None
    return None


def save_summary_cache(video_id: str, summarizer: Summarizer, summary: str) -> None:
    """Save summary for a video/summarizer combo to cache."""
    cache_path = get_summary_cache_path(video_id, summarizer)
    try:
        cache_path.write_text(summary, encoding="utf-8")
        print(f"Cached summary for video {video_id} to {cache_path}")
    except Exception as e:
        print(f"Error saving summary cache for {video_id}: {e}")


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    parsed = urlparse(url)
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            return parse_qs(parsed.query)['v'][0]
    elif parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    raise ValueError(f"Invalid YouTube URL: {url}")
def _download_subtitles_sync(video_id: str, proxy: bool = False) -> Optional[str]:
    """Synchronous helper to download subtitles with caching."""
    # Try cache first
    cached = load_subtitle_cache(video_id)
    if cached is not None:
        return cached

    try:
        if proxy:
            username = os.getenv("WEBSHARE_USERNAME")
            password = os.getenv("WEBSHARE_PASSWORD")
            if not username or not password:
                warning(
                    "WEBSHARE_USERNAME and WEBSHARE_PASSWORD must be set, running without proxy."
                )
                api = YouTubeTranscriptApi()
            else:
                print("Using WebShareProxy to download closed captions")
                api = YouTubeTranscriptApi(
                    proxy_config=WebshareProxyConfig(
                        proxy_username=username,
                        proxy_password=password,
                    )
                )
        else:
            api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=['en'])
        subtitles = " ".join([entry.text for entry in transcript])
        # Save to cache for future use
        save_subtitle_cache(video_id, subtitles)
        return subtitles
    except Exception as e:
        print(f"Error downloading subtitles/captions for {video_id}: {e}")
        return None


async def download_subtitles(video_id: str, proxy: bool = False) -> Optional[str]:
    """Download subtitles or closed captions for a YouTube video."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _download_subtitles_sync(video_id, proxy))




async def process_video(video_url: str, index: int, title: str, summarizer: Summarizer, duration: int = 0, speakers: Optional[str] = None, sched_link: Optional[str] = None, use_summary_cache: bool = True, proxy: bool = False, sleep: int = 0) -> Optional[Dict]:
    """Process a single video: check duration, download subtitles, and summarize."""
    # Check duration
    if duration > 0 and duration < 120:  # Less than 2 minutes
        print(f"Skipping {title} (duration: {duration}s)")
        return None
    
    # Extract video ID
    try:
        video_id = extract_video_id(video_url)
    except ValueError as e:
        print(f"Error: {e}")
        return None
    
    # Optionally sleep before fetching subtitles to avoid hammering YouTube
    if sleep and sleep > 0:
        await asyncio.sleep(sleep)

    # Download subtitles
    subtitles = await download_subtitles(video_id, proxy=proxy)
    if not subtitles:
        print(f"No subtitles available for {title}")

    # Try to load summary from cache first (when enabled), even if subtitles are missing
    summary: Optional[str] = None
    if use_summary_cache:
        summary = load_summary_cache(video_id, summarizer)
        if summary is not None:
            print(f"Reusing cached summary for: {title}")

    # Only attempt to generate a new summary when we have subtitles
    if summary is None:
        if subtitles:
            print(f"Generating summary for: {title}")
            summary = await summarizer.summarize(subtitles, title)
            save_summary_cache(video_id, summarizer, summary)
        else:
            # Include the video with an empty summary when subtitles are unavailable
            summary = ""
    
    result = {
        "index": index,
        "title": title,
        "summary": summary
    }
    
    # Add optional fields if provided
    if speakers:
        result["speakers"] = speakers
    if sched_link:
        result["sched_link"] = sched_link
    
    return result


async def process_playlist(playlist_url: str, summarizer: Optional[Summarizer] = None, limit: Optional[int] = None, refresh_cache: bool = False, use_summary_cache: bool = True, proxy: bool = False, sleep: int = 0) -> Dict[str, Dict]:
    """
    Process a YouTube playlist: download subtitles and generate summaries.
    
    Args:
        playlist_url: URL of the YouTube playlist
        summarizer: Summarizer instance to use (defaults to OpenAISummarizer)
        limit: Maximum number of videos to process (None for all videos)
        refresh_cache: Force refresh playlist data from YouTube (ignore cache)
        
    Returns:
        Dictionary mapping video URLs to their metadata (index, title, summary)
    """
    import yt_dlp
    
    print(f"Processing playlist: {playlist_url}")
    
    # Use default summarizer if none provided
    if summarizer is None:
        summarizer = get_summarizer("anthropic")
    
    # Try to load from cache first (unless refresh is requested)
    videos = None if refresh_cache else load_playlist_cache(playlist_url)
    
    if videos is None:
        # Cache miss - fetch from YouTube
        print("Fetching playlist data from YouTube...")
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
            if 'entries' not in playlist_info:
                print("No videos found in playlist")
                return {}
                
            videos = []
            for entry in playlist_info['entries']:
                if entry:
                    video_id = entry.get('id')
                    if video_id:
                        videos.append({
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'title': entry.get('title', 'Unknown Title'),
                            'duration': entry.get('duration', 0)
                        })
            
            # Save to cache for future use
            save_playlist_cache(playlist_url, videos)
            
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return {}
    
    # Apply limit if specified
    total_videos = len(videos)
    if limit is not None and limit > 0:
        videos = videos[:limit]
        print(f"Found {total_videos} videos in playlist, processing first {len(videos)}")
    else:
        print(f"Found {len(videos)} videos in playlist")
    
    # Extract playlist ID from URL
    playlist_id = None
    parsed = urlparse(playlist_url)
    if parsed.query:
        query_params = parse_qs(parsed.query)
        playlist_id = query_params.get('list', [None])[0]
    
    # Phase 1: fetch subtitles (transcripts) for all eligible videos
    prepared: List[Dict] = []
    for idx, video_info in enumerate(videos, start=1):
        video_url = video_info['url']
        title = video_info['title']
        duration = video_info['duration']

        # Skip very short videos
        if duration > 0 and duration < 120:  # Less than 2 minutes
            print(f"Skipping {title} (duration: {duration}s)")
            continue

        # Construct URL with index parameter (for linking back to playlist)
        if playlist_id:
            indexed_url = f"{video_url}&list={playlist_id}&index={idx}"
        else:
            indexed_url = video_url

        # Extract video ID for subtitle/summary caching
        try:
            video_id = extract_video_id(video_url)
        except ValueError as e:
            print(f"Error: {e}")
            continue

        # Optionally sleep before fetching subtitles to avoid hammering YouTube
        if sleep and sleep > 0:
            await asyncio.sleep(sleep)

        subtitles = await download_subtitles(video_id, proxy=proxy)
        if not subtitles:
            print(f"No subtitles available for {title}")
            # We still include the video; summary generation will be skipped later
            subtitles = ""

        prepared.append(
            {
                "index": idx,
                "video_url": video_url,
                "indexed_url": indexed_url,
                "title": title,
                "duration": duration,
                "video_id": video_id,
                "subtitles": subtitles,
            }
        )

    # Phase 2: generate/load summaries once all subtitles are available
    output: Dict[str, Dict] = {}
    for item in prepared:
        idx = item["index"]
        indexed_url = item["indexed_url"]
        title = item["title"]
        video_id = item["video_id"]
        subtitles = item["subtitles"]

        summary: Optional[str] = None
        if use_summary_cache:
            summary = load_summary_cache(video_id, summarizer)
            if summary is not None:
                print(f"Reusing cached summary for: {title}")

        if summary is None:
            if subtitles:
                print(f"Generating summary for: {title}")
                summary = await summarizer.summarize(subtitles, title)
                save_summary_cache(video_id, summarizer, summary)
            else:
                # No subtitles and no cached summary: include video with blank summary
                summary = ""

        output[indexed_url] = {
            "index": idx,
            "title": title,
            "summary": summary,
        }

    return output

