"""Command-line interface for Summit."""

import asyncio
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .core import process_playlist
from .render import render_markdown, render_marp_deck, render_html_page
from .sched import process_sched_talks
from .summarizers import get_summarizer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process YouTube playlists and generate summary markdown files"
    )
    parser.add_argument(
        "playlist_url",
        help="YouTube playlist URL or sched.com event URL"
    )
    parser.add_argument(
        "-o", "--output-folder",
        dest="output_folder",
        default="summit-outputs",
        help="Output folder for generated files (default: summit-outputs)"
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Conference Summary",
        help="Title to use at the top of rendered outputs (default: 'Conference Summary').",
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Limit the number of videos to process from the playlist"
    )
    parser.add_argument(
        "--cache-bust-youtube",
        action="store_true",
        help="Do not use cached YouTube playlist data (equivalent to refresh for YouTube)."
    )
    parser.add_argument(
        "--cache-bust-sched",
        action="store_true",
        help="Do not use cached sched.com data for this run."
    )
    parser.add_argument(
        "--cache-bust-summary",
        action="store_true",
        help="Do not reuse cached summaries; always regenerate them for this run."
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="For sched.com URLs, skip the first N talks before processing."
    )
    parser.add_argument(
        "--summarizer",
        type=str,
        default="anthropic",
        help="Summarizer backend to use: anthropic, openai, gemini, ollama, or disabled (default: anthropic)."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name for the selected summarizer. For ollama, defaults to 'granite3.3:2b' when not provided."
    )
    parser.add_argument(
        "--summary-length",
        type=int,
        default=800,
        help="Approximate total number of words in each summary (default: 800)."
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=0,
        help="Seconds to sleep between sched.com detail page requests (default: 0)."
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Use configured Webshare proxy for YouTube subtitle requests (default: disabled)."
    )
    
    args = parser.parse_args()

    # Determine summarization strategy and construct summarizer if needed
    strategy = args.summarizer.lower()
    model = args.model
    summary_length = args.summary_length

    # Cache-busting controls
    youtube_refresh = args.cache_bust_youtube
    sched_refresh = args.cache_bust_sched
    use_summary_cache = not args.cache_bust_summary

    summarizer = None
    summarize = True

    if strategy == "disabled":
        summarize = False
        print("Summarization disabled; using Sched descriptions when available.")
    else:
        if strategy == "ollama" and not model:
            model = "granite3.3:2b"

        summarizer_kwargs = {"summary_length": summary_length}
        if model:
            summarizer_kwargs["model"] = model

        print(f"Using {strategy} summarizer" + (f" (model: {model})" if model else "") + "...")
        summarizer = get_summarizer(strategy, **summarizer_kwargs)
    
    # Detect if URL is sched.com or YouTube playlist
    if 'sched.com' in args.playlist_url:
        print("Detected sched.com URL, processing conference talks...")
        data = asyncio.run(process_sched_talks(
            args.playlist_url,
            summarizer=summarizer,
            limit=args.limit,
            refresh_cache=sched_refresh,
            summarize=summarize,
            offset=args.offset,
            sleep=args.sleep,
            use_summary_cache=use_summary_cache,
            proxy=args.proxy,
        ))
    else:
        # Process YouTube playlist
        if strategy == "disabled":
            print("The 'disabled' summarizer is only supported for sched.com URLs. "
                  "Please choose one of: anthropic, openai, gemini, ollama.")
            sys.exit(1)
        print("Starting playlist processing...")
        data = asyncio.run(process_playlist(
            args.playlist_url, 
            summarizer=summarizer, 
            limit=args.limit,
            refresh_cache=youtube_refresh,
            use_summary_cache=use_summary_cache,
            proxy=args.proxy,
            sleep=args.sleep,
        ))
    
    if not data:
        print("No videos were processed successfully.")
        sys.exit(1)
    
    # Determine output folder and ensure it exists
    output_dir = Path(args.output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Render markdown summary
    print(f"\nGenerating markdown summary...")
    markdown = render_markdown(data, title=args.title)
    summary_path = output_dir / f"summary-{timestamp}.md"
    summary_path.write_text(markdown)
    print(f"✓ Summary written to: {summary_path.absolute()}")
    
    print(f"\nGenerating HTML summary...")
    html = render_html_page(data, title=args.title)
    html_path = output_dir / f"summary-{timestamp}.html"
    html_path.write_text(html)
    print(f"✓ HTML summary written to: {html_path.absolute()}")
    
    # Render Marp deck
    print(f"\nGenerating Marp presentation deck...")
    marp_deck = render_marp_deck(data, title=args.title)
    deck_path = output_dir / f"summary-{timestamp}-deck.md"
    deck_path.write_text(marp_deck)
    print(f"✓ Marp deck written to: {deck_path.absolute()}")
    print(f"✓ Marp deck written to: {deck_path.absolute()}")
    
    # Convert to PPTX using Marp CLI
    # print(f"\nConverting to PowerPoint...")
    # pptx_path = output_dir / f"summary-{timestamp}.pptx"
    # try:
    #     result = subprocess.run(
    #         ["marp", str(deck_path), "--pptx", "-o", str(pptx_path)],
    #         capture_output=True,
    #         text=True,
    #         check=True
    #     )
    #     print(f"✓ PowerPoint written to: {pptx_path.absolute()}")
    # except subprocess.CalledProcessError as e:
    #     print(f"⚠ Warning: Could not convert to PPTX. Is Marp CLI installed?")
    #     print(f"  Install with: npm install -g @marp-team/marp-cli")
    #     print(f"  Error: {e.stderr}")
    # except FileNotFoundError:
    #     print(f"⚠ Warning: Marp CLI not found. Skipping PPTX conversion.")
    #     print(f"  Install with: npm install -g @marp-team/marp-cli")
    
    print(f"\n✓ Processed {len(data)} videos")


if __name__ == "__main__":
    main()
