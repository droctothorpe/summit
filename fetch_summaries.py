#!/usr/bin/env python3
import json
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re

def get_playlist_videos(playlist_url):
    """Fetch all videos from the playlist"""
    cmd = ['yt-dlp', '--flat-playlist', '--dump-json', playlist_url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    videos = []
    for line in result.stdout.strip().split('\n'):
        if line:
            video_data = json.loads(line)
            videos.append({
                'index': video_data.get('playlist_index', 0),
                'id': video_data['id'],
                'title': video_data['title'],
                'url': f"https://www.youtube.com/watch?v={video_data['id']}"
            })
    
    # Sort by playlist index
    videos.sort(key=lambda x: x['index'])
    return videos

def get_video_subtitles(video_id):
    """Fetch subtitles for a single video"""
    try:
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--sub-lang', 'en',
            '--sub-format', 'json3',
            '--output', f'/tmp/%(id)s.%(ext)s',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Read the subtitle file
        subtitle_file = f'/tmp/{video_id}.en.json3'
        try:
            with open(subtitle_file, 'r') as f:
                subtitle_data = json.load(f)
                
            # Extract text from subtitles
            text_parts = []
            for event in subtitle_data.get('events', []):
                if 'segs' in event:
                    for seg in event['segs']:
                        if 'utf8' in seg:
                            text_parts.append(seg['utf8'])
            
            full_text = ''.join(text_parts)
            # Clean up the text
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            # Clean up the file
            subprocess.run(['rm', '-f', subtitle_file], capture_output=True)
            
            return full_text
        except FileNotFoundError:
            return None
            
    except Exception as e:
        print(f"Error fetching subtitles for {video_id}: {e}")
        return None

def summarize_text(text, title):
    """Generate a summary using OpenAI API"""
    import os
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        prompt = f"""Summarize this conference talk transcript in about half a page to a page. Focus on the key points, main ideas, and takeaways. The talk is titled: "{title}"

Transcript:
{text[:15000]}"""  # Limit to avoid token limits
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries of technical conference talks."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Fallback to simple extraction
        if len(text) > 1000:
            return text[:1000] + "..."
        return text

async def process_video(video, executor):
    """Process a single video asynchronously"""
    print(f"Processing [{video['index']}]: {video['title']}")
    
    loop = asyncio.get_event_loop()
    subtitles = await loop.run_in_executor(executor, get_video_subtitles, video['id'])
    
    if subtitles and len(subtitles) > 200:
        # Generate a summary using AI
        summary = await loop.run_in_executor(executor, summarize_text, subtitles, video['title'])
    else:
        summary = "No subtitles available for this video."
    
    return {
        'index': video['index'],
        'title': video['title'],
        'url': video['url'],
        'summary': summary
    }

async def main():
    playlist_url = "https://www.youtube.com/playlist?list=PLj6h78yzYM2MP0QhYFK8HOb8UqgbIkLMc"
    
    print("Fetching playlist videos...")
    videos = get_playlist_videos(playlist_url)
    print(f"Found {len(videos)} videos")
    
    # Process videos asynchronously
    executor = ThreadPoolExecutor(max_workers=10)
    tasks = [process_video(video, executor) for video in videos]
    
    results = await asyncio.gather(*tasks)
    
    # Sort by index
    results.sort(key=lambda x: x['index'])
    
    # Generate markdown
    markdown_lines = []
    for result in results:
        markdown_lines.append(f"## {result['title']}\n")
        markdown_lines.append(f"{result['url']}\n")
        markdown_lines.append(f"\n{result['summary']}\n")
        markdown_lines.append("\n---\n")
    
    # Write to file
    with open('summit_talks.md', 'w') as f:
        f.write('\n'.join(markdown_lines))
    
    print(f"\nGenerated summit_talks.md with {len(results)} talks")

if __name__ == '__main__':
    asyncio.run(main())
