"""`<!-- autoindex -->` マーカーを兄弟記事の一覧に差し替える MkDocs フック。

対象は `YYYY-MM-DD-slug.md` 形式のファイル。タイトルは H1 から取得し、
日付の降順、年ごとに見出しを付けて一覧化する。年ごとのサブディレクトリ
（例: `2025/2025-12-31-foo.md`）にも対応する。
"""

from __future__ import annotations

import re
from itertools import groupby
from pathlib import Path

MARKER = "<!-- autoindex -->"
FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")


def _extract_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _build_listing(posts_dir: Path) -> str:
    entries: list[tuple[str, str, str, str]] = []
    for path in posts_dir.rglob("*.md"):
        if path.name == "index.md":
            continue
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        year = m.group(1)
        date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        title = _extract_title(path.read_text(encoding="utf-8"), m.group(4))
        rel = path.relative_to(posts_dir).as_posix()
        entries.append((year, date, title, rel))
    if not entries:
        return "_（まだ記事がありません）_"
    entries.sort(key=lambda e: e[1], reverse=True)
    sections: list[str] = []
    for year, group in groupby(entries, key=lambda e: e[0]):
        sections.append(f"### {year}年")
        sections.append(
            "\n".join(f"- {date} [{title}]({rel})" for _, date, title, rel in group)
        )
    return "\n\n".join(sections)


def on_page_markdown(markdown: str, page, config, files) -> str:
    if MARKER not in markdown:
        return markdown
    posts_dir = (Path(config["docs_dir"]) / page.file.src_path).parent
    return markdown.replace(MARKER, _build_listing(posts_dir))
