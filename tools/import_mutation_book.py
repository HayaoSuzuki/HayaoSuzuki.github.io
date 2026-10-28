"""Import the textbook from an explicitly pinned hoimin checkout."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

SOURCE_REVISION = "90b5f2963f4a0a24bb659e39eb293e0224333b19"
SOURCE_REPOSITORY = "https://github.com/HayaoSuzuki/hoimin.git"


def import_book(source: Path, destination: Path) -> None:
    source = source.resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    remote = subprocess.check_output(
        ["git", "-C", str(source), "remote", "get-url", "origin"], text=True
    ).strip()
    if revision != SOURCE_REVISION or remote.removesuffix(".git") != SOURCE_REPOSITORY.removesuffix(
        ".git"
    ):
        raise ValueError("Source must be the pinned HayaoSuzuki/hoimin commit")
    if subprocess.check_output(
        ["git", "-C", str(source), "status", "--porcelain", "--", "docs/book"], text=True
    ).strip():
        raise ValueError("Source textbook has uncommitted changes")
    book = source / "docs/book"
    if not (book / "index.md").is_file() or not (book / "assets/shipping-workshop.zip").is_file():
        raise ValueError("Pinned textbook or workshop archive is missing")
    site_root = Path(__file__).resolve().parents[1]
    expected = site_root / "docs/mutation-testing"
    if (
        destination != expected
        or destination.is_symlink()
        or destination.resolve().parent != (site_root / "docs").resolve()
    ):
        raise ValueError("Destination must be this site's generated textbook directory")
    if destination.exists():
        if not (destination / ".source-revision").is_file():
            raise ValueError("Refusing to replace a directory without the generated marker")
        shutil.rmtree(destination)
    tracked = subprocess.check_output(
        ["git", "-C", str(source), "ls-files", "-z", "--", "docs/book"], text=True
    ).split("\0")
    destination.mkdir(parents=True)
    for filename in filter(None, tracked):
        relative = Path(filename).relative_to("docs/book")
        if relative.parts[0] == "examples" or relative.name == ".gitattributes":
            continue
        original = source / filename
        if not original.resolve().is_relative_to(book.resolve()):
            raise ValueError("Tracked source file escapes the textbook directory")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    (destination / ".source-revision").write_text(SOURCE_REVISION + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    import_book(args.source, Path(__file__).resolve().parents[1] / "docs/mutation-testing")


if __name__ == "__main__":
    main()
