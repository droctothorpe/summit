"""Rendering utilities for Summit (markdown and Marp)."""

import html
from typing import Dict


def render_markdown(data: Dict[str, Dict], title: str = "Conference Summary") -> str:
    """Render playlist/conference data as markdown."""
    # Sort by index
    sorted_items = sorted(data.items(), key=lambda x: x[1]["index"])

    markdown_parts = []

    if title:
        markdown_parts.append(f"# {title}\n\n---\n\n")
    for url, info in sorted_items:
        lines = [f"## {info['title']}"]

        # Event / YouTube / Deck / event_type line (if sched_link is available)
        if 'sched_link' in info:
            line = f"\n\n[Event]({info['sched_link']}) | [Youtube]({url})"
            deck_url = info.get('deck_url')
            if deck_url:
                line += f" | [Deck]({deck_url})"
            event_type = info.get('event_type')
            if event_type:
                line += f" | {event_type}"
            else:
                print("no event_type")
            lines.append(line)

        # Summary content
        lines.append(f"\n\n{info['summary']}")

        # Separator between talks
        lines.append("\n\n---")

        section = "".join(lines)
        markdown_parts.append(section)

    return "\n\n".join(markdown_parts)


def render_html_page(data: Dict[str, Dict], title: str = "Conference Summary") -> str:
    sorted_items = sorted(data.items(), key=lambda x: x[1]["index"])

    page_title = html.escape(title or "Conference Summary")

    # Detect whether any items have an event_type; used to decide if type filter is shown
    has_event_types = any((info.get("event_type") or "").strip() for _, info in sorted_items)

    html_parts = []
    html_parts.append(
        """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
"""
    )

    # Title tag with escaped page title
    html_parts.append(f"  <title>{page_title}</title>\n")

    html_parts.append(
        """  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
  <style>
    body {
      min-height: 100vh;
    }

    .theme-toggle {
      position: relative;
      width: 3.25rem;
      height: 1.6rem;
      border-radius: 999px;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-width: 1px;
      overflow: hidden;
    }

    .theme-toggle-track {
      position: absolute;
      inset: 0.15rem;
      border-radius: 999px;
      opacity: 0.65;
    }

    .theme-toggle-handle {
      position: relative;
      width: 1.3rem;
      height: 1.3rem;
      border-radius: 999px;
      background-color: var(--bs-body-bg);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      transition: transform 0.18s ease;
    }

    .theme-toggle[data-theme="light"] .theme-toggle-handle {
      transform: translateX(-0.7rem);
    }

    .theme-toggle[data-theme="dark"] .theme-toggle-handle {
      transform: translateX(0.7rem);
    }

    .talk-actions {
      display: flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.85rem;
    }

    .talk-action-link {
      border: none;
      padding: 0;
      margin: 0;
      background: none;
      color: inherit;
      font: inherit;
      cursor: pointer;
    }

    .talk-action-separator {
      opacity: 0.7;
    }

    .controls {
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(8px);
    }
  </style>
</head>
<body class="bg-body text-body d-flex flex-column align-items-center py-4 px-3">
  <div class="w-100" style="max-width: 1120px;">
    <header class="mb-3">
      <div class="d-flex align-items-center justify-content-between mb-2 flex-wrap gap-2">
        <div class="me-auto">
"""
    )

    # Visible page title in header
    html_parts.append(f"          <h1 class=\"h3 mb-0\">{page_title}</h1>\n")

    html_parts.append(
        """        </div>
        <button
          id="themeToggle"
          type="button"
          class="btn btn-sm btn-outline-secondary theme-toggle"
          aria-label="Toggle light and dark theme"
          data-theme="dark"
        >
          <span class="theme-toggle-track bg-body-secondary"></span>
          <span class="theme-toggle-handle text-body" aria-hidden="true">
            <i class="bi bi-sun-fill" data-icon-light></i>
            <i class="bi bi-moon-stars-fill d-none" data-icon-dark></i>
          </span>
        </button>
      </div>
    </header>
    <section class="controls d-flex flex-wrap align-items-center gap-3 border rounded-3 px-3 py-2 mb-3 bg-body-secondary bg-opacity-75">
"""
    )

    # Type filter label: only render when we actually have event types (sched.com inputs)
    if has_event_types:
        html_parts.append(
            "      <label for=\"typeFilter\" class=\"d-flex align-items-center gap-2 small mb-0\">\n"
            "        <span class=\"text-body-secondary\">Type</span>\n"
            "        <select id=\"typeFilter\" class=\"form-select form-select-sm\" style=\"width: auto;\">\n"
            "          <option value=\"\">All types</option>\n"
            "        </select>\n"
            "      </label>\n"
        )

    html_parts.append(
        """      <div class="d-flex align-items-center gap-3 small">
        <div class="form-check form-switch mb-0">
          <input class="form-check-input" type="checkbox" role="switch" id="showHiddenToggle">
          <label class="form-check-label" for="showHiddenToggle">Show hidden</label>
        </div>
        <div class="form-check form-switch mb-0">
          <input class="form-check-input" type="checkbox" role="switch" id="onlySavedToggle">
          <label class="form-check-label" for="onlySavedToggle">Saved</label>
        </div>
      </div>
      <div id="resultCount" class="ms-auto small text-body-secondary text-nowrap"></div>
    </section>
    <main id="talkList" class="d-flex flex-column gap-3">
"""
    )

    for url, info in sorted_items:
        title = info.get("title", "")
        sched_link = info.get("sched_link")
        deck_url = info.get("deck_url")
        event_type = (info.get("event_type") or "").strip()
        summary = info.get("summary", "") or ""

        title_html = html.escape(title)
        event_type_attr = html.escape(event_type)
        item_id_attr = html.escape(url or sched_link or title or "")

        links = []
        if sched_link:
            links.append(
                f'<a href="{html.escape(sched_link)}" target="_blank" rel="noopener noreferrer">Event</a>'
            )
        if url:
            links.append(
                f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">YouTube</a>'
            )
        if deck_url:
            links.append(
                f'<a href="{html.escape(deck_url)}" target="_blank" rel="noopener noreferrer">Deck</a>'
            )

        links_html = " \u00b7 ".join(links) if links else ""

        if event_type:
            meta_text = links_html + (" \u00b7 " if links_html else "") + html.escape(event_type)
        else:
            meta_text = links_html

        html_parts.append(
            f'      <article class="talk card border rounded-3 shadow-sm" data-type="{event_type_attr}" data-id="{item_id_attr}">\n'
            f'        <div class="card-body">\n'
            f'          <div class="d-flex flex-column gap-1 mb-1">\n'
            f'            <h2 class="h6 mb-0">{title_html}</h2>\n'
            f'            <div class="d-flex flex-wrap align-items-center gap-2 small text-body-secondary">\n'
            f'              <span>{meta_text}</span>\n'
            "            </div>\n"
            "          </div>\n"
            "          <div class=\"talk-actions mb-2 text-body-secondary\">\n"
            f'            <span class="talk-action-link btn-hide" data-id="{item_id_attr}">Hide</span>\n'
            "            <span class=\"talk-action-separator\">·</span>\n"
            f'            <span class="talk-action-link btn-save" data-id="{item_id_attr}">Save</span>\n'
            "          </div>\n"
            f'          <div class="mt-1 small" style="white-space: pre-line;">{html.escape(summary)}</div>\n'
            "        </div>\n"
            "      </article>\n"
        )

    html_parts.append(
        """    </main>
  </div>
  <script>
    document.addEventListener('DOMContentLoaded', function () {
      const talks = Array.from(document.querySelectorAll('.talk'));
      const select = document.getElementById('typeFilter');
      const countEl = document.getElementById('resultCount');
      const themeToggle = document.getElementById('themeToggle');
      const showHiddenToggle = document.getElementById('showHiddenToggle');
      const onlySavedToggle = document.getElementById('onlySavedToggle');

      const STORAGE_HIDDEN = 'summit_hidden_talks';
      const STORAGE_SAVED = 'summit_saved_talks';
      const STORAGE_SHOW_HIDDEN = 'summit_show_hidden';
      const STORAGE_ONLY_SAVED = 'summit_only_saved';

      function loadSet(key) {
        try {
          const raw = window.localStorage.getItem(key);
          if (!raw) return new Set();
          const arr = JSON.parse(raw);
          return new Set(Array.isArray(arr) ? arr : []);
        } catch (e) {
          return new Set();
        }
      }

      function saveSet(key, set) {
        try {
          window.localStorage.setItem(key, JSON.stringify(Array.from(set)));
        } catch (e) {
          // ignore storage errors
        }
      }

      function loadBool(key, defaultValue) {
        try {
          const raw = window.localStorage.getItem(key);
          if (raw === null) return defaultValue;
          return raw === 'true';
        } catch (e) {
          return defaultValue;
        }
      }

      function saveBool(key, value) {
        try {
          window.localStorage.setItem(key, value ? 'true' : 'false');
        } catch (e) {
          // ignore storage errors
        }
      }

      const hiddenSet = loadSet(STORAGE_HIDDEN);
      const savedSet = loadSet(STORAGE_SAVED);
      let showHidden = loadBool(STORAGE_SHOW_HIDDEN, false);
      let onlySaved = loadBool(STORAGE_ONLY_SAVED, false);

      if (showHiddenToggle) {
        showHiddenToggle.checked = showHidden;
      }
      if (onlySavedToggle) {
        onlySavedToggle.checked = onlySaved;
      }

      const types = new Set();
      talks.forEach(function (el) {
        const t = el.getAttribute('data-type');
        if (t) {
          types.add(t);
        }
      });

      Array.from(types).sort().forEach(function (t) {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        select.appendChild(opt);
      });

      function updateTalkButtons() {
        talks.forEach(function (el) {
          const id = el.getAttribute('data-id') || '';
          const isHidden = hiddenSet.has(id);
          const isSaved = savedSet.has(id);
          const hideBtn = el.querySelector('.btn-hide');
          const saveBtn = el.querySelector('.btn-save');

          if (hideBtn) {
            hideBtn.textContent = isHidden ? 'Unhide' : 'Hide';
          }
          if (saveBtn) {
            saveBtn.textContent = isSaved ? 'Unsave' : 'Save';
          }
        });
      }

      function updateVisibility() {
        const value = select.value;
        let visible = 0;
        talks.forEach(function (el) {
          const t = el.getAttribute('data-type') || '';
          const id = el.getAttribute('data-id') || '';
          const isHidden = hiddenSet.has(id);
          const isSaved = savedSet.has(id);

          let shouldShow = true;
          if (value && t !== value) {
            shouldShow = false;
          }
          if (!showHidden && isHidden) {
            shouldShow = false;
          }
          if (onlySaved && !isSaved) {
            shouldShow = false;
          }

          if (shouldShow) {
            el.classList.remove('d-none');
            visible += 1;
          } else {
            el.classList.add('d-none');
          }
        });
        if (countEl) {
          const total = talks.length;
          if (!select.value) {
            countEl.textContent = visible + ' of ' + total + ' sessions';
          } else {
            countEl.textContent = visible + ' of ' + total + ' sessions · type: ' + select.value;
          }
        }
      }

      select.addEventListener('change', function () {
        updateVisibility();
      });

      if (showHiddenToggle) {
        showHiddenToggle.addEventListener('change', function () {
          showHidden = !!showHiddenToggle.checked;
          saveBool(STORAGE_SHOW_HIDDEN, showHidden);
          updateVisibility();
        });
      }

      if (onlySavedToggle) {
        onlySavedToggle.addEventListener('change', function () {
          onlySaved = !!onlySavedToggle.checked;
          saveBool(STORAGE_ONLY_SAVED, onlySaved);
          updateVisibility();
        });
      }

      document.querySelectorAll('.btn-hide').forEach(function (btn) {
        btn.addEventListener('click', function () {
          const id = btn.getAttribute('data-id') || '';
          if (!id) return;
          if (hiddenSet.has(id)) {
            hiddenSet.delete(id);
          } else {
            hiddenSet.add(id);
          }
          saveSet(STORAGE_HIDDEN, hiddenSet);
          updateTalkButtons();
          updateVisibility();
        });
      });

      document.querySelectorAll('.btn-save').forEach(function (btn) {
        btn.addEventListener('click', function () {
          const id = btn.getAttribute('data-id') || '';
          if (!id) return;
          if (savedSet.has(id)) {
            savedSet.delete(id);
          } else {
            savedSet.add(id);
          }
          saveSet(STORAGE_SAVED, savedSet);
          updateTalkButtons();
          updateVisibility();
        });
      });

      updateTalkButtons();
      updateVisibility();

      if (themeToggle) {
        const sunIcon = themeToggle.querySelector('[data-icon-light]');
        const moonIcon = themeToggle.querySelector('[data-icon-dark]');

        function applyThemeToToggle(theme) {
          themeToggle.setAttribute('data-theme', theme);
          if (sunIcon && moonIcon) {
            if (theme === 'dark') {
              sunIcon.classList.add('d-none');
              moonIcon.classList.remove('d-none');
            } else {
              sunIcon.classList.remove('d-none');
              moonIcon.classList.add('d-none');
            }
          }
        }

        // Initialize slider position and icon from current theme
        const initialTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        applyThemeToToggle(initialTheme);

        themeToggle.addEventListener('click', function () {
          const htmlEl = document.documentElement;
          const current = htmlEl.getAttribute('data-bs-theme') || 'light';
          const next = current === 'dark' ? 'light' : 'dark';
          htmlEl.setAttribute('data-bs-theme', next);
          applyThemeToToggle(next);
        });
      }
    });
  </script>
</body>
</html>
"""
    )

    return "".join(html_parts)


def render_marp_deck(data: Dict[str, Dict], title: str = "Conference Summary") -> str:
    """Render playlist/conference data as a Marp presentation deck."""
    # Sort by index
    sorted_items = sorted(data.items(), key=lambda x: x[1]["index"])

    # Marp header with inverted theme
    marp_header = """---
marp: true
theme: default
class: invert
paginate: true
---
"""

    slides = [marp_header]

    # Optional title slide
    if title:
        slides.append(f"# {title}\n\n---\n\n")

    for url, info in sorted_items:
        # Title card for the talk
        header_parts = [f"## {info['title']}\n"]

        if 'sched_link' in info:
            line = f"\n[Event]({info['sched_link']}) | [Youtube]({url})"
            deck_url = info.get('deck_url')
            if deck_url:
                line += f" | [Deck]({deck_url})"
            event_type = info.get('event_type')
            if event_type:
                line += f" | {event_type}"
            header_parts.append(line + "\n")

        # Title slide (no body content)
        slides.append("".join(header_parts) + "\n---\n\n")

        summary = info['summary']
        paragraphs = summary.split('\n\n') if summary else [""]

        # Chunk summary into ~1000 character slides
        chunks = []
        current = []
        current_len = 0
        max_len = 1000

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) > max_len and current:
                chunks.append('\n\n'.join(current))
                current = [para]
                current_len = len(para)
            else:
                current.append(para)
                current_len += len(para)
        if current:
            chunks.append('\n\n'.join(current))

        if not chunks:
            continue

        # For each chunk, create a slide with just the summary content
        for chunk in chunks:
            parts = [f"{chunk}\n", "\n---\n\n"]
            slides.append("".join(parts))

    # Remove trailing separator from the very last slide
    if len(slides) > 1:
        last = slides[-1]
        marker = "\n---"
        if marker in last:
            # Strip everything from the last '---' marker onward
            prefix = last.rsplit(marker, 1)[0]
            slides[-1] = prefix + "\n"

    return "".join(slides)
