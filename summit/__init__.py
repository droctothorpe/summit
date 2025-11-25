"""Summit - YouTube Playlist Summarizer

A library for downloading YouTube playlist subtitles and generating summaries.
"""

from .core import process_playlist
from .sched import process_sched_talks, scrape_sched_talks
from .render import render_markdown, render_marp_deck
from .summarizers import Summarizer, AnthropicSummarizer, GeminiSummarizer, OpenAISummarizer, OllamaSummarizer, get_summarizer

__version__ = "0.1.0"
__all__ = [
    "process_playlist",
    "process_sched_talks",
    "scrape_sched_talks",
    "render_markdown",
    "render_marp_deck",
    "Summarizer",
    "AnthropicSummarizer",
    "GeminiSummarizer",
    "OpenAISummarizer",
    "OllamaSummarizer",
    "get_summarizer",
]
