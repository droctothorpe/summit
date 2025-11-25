# ➕ Summit

Summit is a library for summarizing conferences.

[Here's](https://droctothorpe.github.io/summit/) an example output.

Please note, GitHub blocks the javascript from executing, so the light/dark and
hide/save functionality is disabled. To preview this, download and open the
[html file](docs/index.html) locally.

---

## Design

Summit works by:

- Downloading presentation subtitles from YouTube videos (with optional proxy support to bypass rate limits imposed by YouTube)
- Summarizing talks using pluggable LLM backends including:
  -  Anthropic
  -  OpenAI
  -  Gemini
  -  Ollama
- Rendering easily consumable outputs as:
  - Markdown summary
  - Filterable HTML page
  - Marp markdown deck for slides



---

## Installation

From a checkout of this repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Backends like Anthropic/OpenAI/Gemini/Ollama require you to have their respective Python SDKs and environment variables configured; see the summarizer section below.

---

## CLI overview

The main entrypoint is the `summit` command:

```bash
summit PLAYLIST_OR_SCHED_URL [options]
```

### Positional argument

- **`playlist_url`**  
  - YouTube playlist URL, e.g. `https://www.youtube.com/playlist?list=...`  
  - Or sched.com event URL, e.g. `https://kccnceu2025.sched.com`.

### Core options

- **`-o, --output-folder`**  
  Folder where outputs are written. Default: `summit-outputs/`. Three files are created per run:
  - `summary-YYYYMMDD-HHMMSS.md` – markdown
  - `summary-YYYYMMDD-HHMMSS.html` – interactive HTML
  - `summary-YYYYMMDD-HHMMSS-deck.md` – Marp deck

- **`--title`**  
  Title used at the top of the markdown, HTML page, and Marp deck.  
  Default: `Conference Summary`.

- **`-l, --limit`**  
  Limit the number of talks/videos processed from the playlist/sched feed. Mostly used for testing / validation.

- **`--summary-length`**  
  Approximate word count per summary (passed through to the summarizer). Default: `800`.

### Caching and refresh

The application caches extensively to optimize execution time and reduce
redundant network calls. Scraped metadata and captions as well as generated
summaries are cached in `~/.cache/summit`. You can selectively bypass specific
caches with:

- **`--cache-bust-youtube`**  
  Ignore cached YouTube playlist metadata; re-fetch playlist info.

- **`--cache-bust-sched`**  
  Ignore cached sched.com scrape; re-fetch the schedule.

- **`--cache-bust-summary`**  
  Force regeneration of summaries instead of reusing cached summaries.

### Source-specific options

- **`--offset` (sched.com only)**  
  Skip the first N talks before processing, useful to resume from later in a schedule.

- **Duration filter (YouTube playlists)**  
  Videos shorter than 2 minutes are automatically skipped and not summarized.

### Summarizer selection

- **`--summarizer`** (default: `anthropic`)  
  One of:
  - `anthropic`
  - `openai`
  - `gemini`
  - `ollama`
  - `disabled` (no LLM; for sched.com this uses the provided descriptions)

- **`--model`**  
  Model name for the chosen backend. For Ollama, if you omit this, the default is `granite3.3:2b`.

### Rate limiting and proxy

- **`--sleep`**  
  Number of seconds to sleep between sched.com detail-page requests. This helps
  with sched.com rate-limiting. Default: `0`.

- **`--proxy`**  
  Use the configured Webshare proxy for YouTube subtitle requests.

  When `--proxy` is set, Summit looks for:

  - `WEBSHARE_USERNAME`
  - `WEBSHARE_PASSWORD`

  Using Webshare (or another proxy configured this way) is strongly recommended for **large playlists**, because it reduces the chance of YouTube rate limiting subtitle requests.

---

## Example usage

### Summarize a YouTube playlist

```bash
# Basic: Anthropic summarizer, default title
summit "https://www.youtube.com/playlist?list=PL..."

# Custom title and output folder
summit "https://www.youtube.com/playlist?list=PL..." \
  --title "KubeCon NA 2025" \
  -o kubecon-na-2025

# Use Ollama locally
summit "https://www.youtube.com/playlist?list=PL..." \
  --summarizer ollama \
  --model granite3.3:2b

# Large playlist with Webshare proxy enabled
export WEBSHARE_USERNAME=your_username
export WEBSHARE_PASSWORD=your_password

summit "https://www.youtube.com/playlist?list=PL..." \
  --summarizer ollama \
  --proxy
```

### Summarize a sched.com event

```bash
# Use Anthropic to summarize all talks for a conference
summit "https://kccnceu2025.sched.com" \
  --title "KubeCon + CloudNativeCon EU 2025" \
  --summarizer anthropic

# Resume from later in the schedule and limit total talks
summit "https://kccnceu2025.sched.com" \
  --offset 40 \
  --limit 60

# Use descriptions only (no LLM)
summit "https://kccnceu2025.sched.com" --summarizer disabled
```

---

## Python API

You can also call the core functions directly:

```python
import asyncio
from summit import process_playlist, process_sched_talks, render_markdown, render_html_page, render_marp_deck, get_summarizer

async def main():
    summarizer = get_summarizer("anthropic", summary_length=800)

    # YouTube playlist
    data = await process_playlist("https://www.youtube.com/playlist?list=PL...", summarizer=summarizer)

    # Or sched.com event
    # data = await process_sched_talks("https://kccnceu2025.sched.com", summarizer=summarizer)

    md = render_markdown(data, title="Conference Summary")
    html = render_html_page(data, title="Conference Summary")
    deck = render_marp_deck(data, title="Conference Summary")

asyncio.run(main())
```

The data structure returned by `process_playlist` / `process_sched_talks` is a dict mapping URLs to metadata:

```python
{
    "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&index=1": {
        "index": 1,
        "title": "Talk title",
        "summary": "...",  # may be empty if subtitles were unavailable
        # optional: "sched_link", "deck_url", "event_type", etc.
    }
}
```

## TODO

Disclaimer: this project was mostly vibe-coded so I can't vouch for the code quality.

- Implement tests.
- Implement UI interface. 
- Setup PyPi release process.
- Implement pre-commit hooks.

---

## License

Summit is licensed under the [Apache License, Version 2.0](LICENSE).
