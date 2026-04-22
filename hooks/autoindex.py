"""`<!-- autoindex -->` マーカーを兄弟記事の一覧に差し替える MkDocs フック。

対象は `YYYY-MM-DD-slug.md` 形式のファイル。タイトルは H1 から取得し、
日付の降順で並べる。
"""

from __future__ import annotations

import re
from pathlib import Path

MARKER = "<!-- autoindex -->"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")


def _extract_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _build_listing(posts_dir: Path) -> str:
    entries: list[tuple[str, str, str]] = []
    for path in posts_dir.iterdir():
        if not path.is_file() or path.name == "index.md":
            continue
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        date, slug = m.group(1), m.group(2)
        title = _extract_title(path.read_text(encoding="utf-8"), slug)
        entries.append((date, title, path.name))
    entries.sort(key=lambda e: e[0], reverse=True)
    if not entries:
        return "_（まだ記事がありません）_"
    return "\n".join(f"- {date} [{title}]({fname})" for date, title, fname in entries)


def on_page_markdown(markdown: str, page, config, files) -> str:
    if MARKER not in markdown:
        return markdown
    posts_dir = (Path(config["docs_dir"]) / page.file.src_path).parent
    return markdown.replace(MARKER, _build_listing(posts_dir))
