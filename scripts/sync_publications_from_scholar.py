#!/usr/bin/env python3
"""Sync Google Scholar publications into Jekyll _publications markdown files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PLACEHOLDER_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-paper-title-number-\d+\.md$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch publications from Google Scholar and generate _publications markdown files."
    )
    parser.add_argument(
        "--config",
        default="_config.yml",
        help="Path to Jekyll _config.yml (default: _config.yml).",
    )
    parser.add_argument(
        "--output-dir",
        default="_publications",
        help="Directory where publication markdown files are written (default: _publications).",
    )
    parser.add_argument(
        "--scholar-url",
        default=None,
        help="Override Google Scholar profile URL. If omitted, reads author.googlescholar from _config.yml.",
    )
    parser.add_argument(
        "--max-publications",
        type=int,
        default=None,
        help="Optional max number of publications to sync.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without writing/deleting files.",
    )
    return parser.parse_args()


def read_scholar_url(config_path: Path) -> str:
    pattern = re.compile(r"^\s*googlescholar\s*:\s*(.+?)\s*$")
    for line in config_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        if value:
            return value
    raise ValueError(f"Could not find a non-empty 'googlescholar' entry in {config_path}.")


def extract_scholar_user_id(scholar_url: str) -> str:
    parsed = urlparse(scholar_url)
    user = parse_qs(parsed.query).get("user", [])
    if not user:
        raise ValueError(
            f"Google Scholar URL must include a 'user=' query parameter. Got: {scholar_url}"
        )
    return user[0]


def cleanup_text(value: str) -> str:
    cleaned = str(value).replace("{", "").replace("}", "").replace("\\", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def yaml_quote(value: str) -> str:
    return cleanup_text(value).replace("'", "''")


def slugify(text: str) -> str:
    slug = cleanup_text(text).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "untitled-publication"


def normalize_authors(author_field: object) -> str:
    if isinstance(author_field, list):
        authors = [cleanup_text(a) for a in author_field if cleanup_text(a)]
        return ", ".join(authors)

    author_text = cleanup_text(author_field or "")
    if not author_text:
        return "Unknown Author"

    split_authors = [cleanup_text(a) for a in re.split(r"\s+and\s+", author_text) if cleanup_text(a)]
    if len(split_authors) > 1:
        return ", ".join(split_authors)
    return author_text


def parse_year(value: object) -> str:
    year_text = cleanup_text(value or "")
    match = re.search(r"(19|20)\d{2}", year_text)
    return match.group(0) if match else "1900"


def build_citation(authors: str, title: str, venue: str, year: str) -> str:
    citation = f'{authors}, "{title}."'
    if venue:
        citation += f" {venue},"
    citation += f" {year}."
    return citation


def build_markdown(
    title: str,
    permalink_slug: str,
    date_str: str,
    category: str,
    venue: str,
    paper_url: str,
    citation: str,
) -> str:
    lines = [
        "---",
        f"title: '{yaml_quote(title)}'",
        "collection: publications",
        f"category: {category}",
        f"permalink: /publication/{permalink_slug}",
        f"date: {date_str}",
        f"venue: '{yaml_quote(venue)}'",
        "source: google_scholar",
    ]
    if paper_url:
        lines.append(f"paperurl: '{yaml_quote(paper_url)}'")
    lines.append(f"citation: '{yaml_quote(citation)}'")
    lines.append("---")
    lines.append("")
    lines.append("Synced from Google Scholar.")
    lines.append("")
    return "\n".join(lines)


def choose_venue(bib: dict[str, object]) -> str:
    for key in ("venue", "journal", "booktitle", "publisher", "conference"):
        value = cleanup_text(bib.get(key, ""))
        if value:
            return value
    return "Unknown venue"


def choose_paper_url(pub: dict[str, object], bib: dict[str, object]) -> str:
    candidates = [
        pub.get("pub_url"),
        bib.get("url"),
        pub.get("eprint_url"),
        pub.get("citedby_url"),
    ]
    for value in candidates:
        cleaned = cleanup_text(value or "")
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
    return ""


def choose_category(pub: dict[str, object], bib: dict[str, object]) -> str:
    pub_type = cleanup_text(pub.get("pub_type", "")).lower()
    entry_type = cleanup_text(bib.get("ENTRYTYPE", "")).lower()
    venue = cleanup_text(bib.get("venue", "")).lower()
    journal = cleanup_text(bib.get("journal", "")).lower()

    book_markers = ("book", "monograph", "chapter")
    if any(marker in pub_type for marker in book_markers) or any(marker in entry_type for marker in book_markers):
        return "books"

    conference_markers = ("conference", "proceeding", "workshop", "symposium")
    if (
        any(marker in pub_type for marker in conference_markers)
        or any(marker in entry_type for marker in conference_markers)
        or any(marker in venue for marker in conference_markers)
    ):
        return "conferences"

    if journal:
        return "manuscripts"

    return "manuscripts"


def load_previous_manifest(manifest_path: Path) -> list[str]:
    if not manifest_path.exists():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = payload.get("files", [])
        if isinstance(files, list):
            return [str(name) for name in files]
    except (json.JSONDecodeError, OSError):
        pass
    return []


def is_managed_by_scholar(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "source: google_scholar" in text


def main() -> int:
    args = parse_args()

    try:
        from scholarly import scholarly  # imported lazily for clearer error handling
    except ModuleNotFoundError:
        print(
            "ERROR: Missing Python dependency 'scholarly'. Run via ./scripts/update_publications.sh.",
            file=sys.stderr,
        )
        return 1

    repo_root = Path.cwd()
    config_path = repo_root / args.config
    output_dir = repo_root / args.output_dir
    manifest_path = output_dir / ".google_scholar_manifest.json"

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    scholar_url = args.scholar_url or read_scholar_url(config_path)
    scholar_user_id = extract_scholar_user_id(scholar_url)

    print(f"Fetching Google Scholar profile for user id: {scholar_user_id}")
    author = scholarly.search_author_id(scholar_user_id)
    try:
        author = scholarly.fill(author, sections=["publications"])
    except TypeError:
        author = scholarly.fill(author)

    publications = author.get("publications", [])
    if args.max_publications is not None:
        publications = publications[: args.max_publications]

    if not publications:
        print(
            "ERROR: Google Scholar returned zero publications. Existing files were left unchanged.",
            file=sys.stderr,
        )
        return 2

    managed_files = set(load_previous_manifest(manifest_path))
    generated_files: list[str] = []
    used_filenames: set[str] = set()

    for index, pub_summary in enumerate(publications, start=1):
        try:
            pub = scholarly.fill(pub_summary)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: Skipping publication #{index} due to fetch error: {exc}")
            continue

        bib = pub.get("bib", {})
        title = cleanup_text(bib.get("title", ""))
        if not title:
            print(f"WARNING: Skipping publication #{index} because title is missing.")
            continue

        year = parse_year(bib.get("pub_year") or bib.get("year"))
        date_str = f"{year}-01-01"
        slug = f"{date_str}-{slugify(title)}"
        filename = f"{slug}.md"
        suffix = 2
        while True:
            target_path = output_dir / filename
            managed_existing = filename in managed_files or is_managed_by_scholar(target_path)
            if filename not in used_filenames and (not target_path.exists() or managed_existing):
                break
            filename = f"{slug}-{suffix}.md"
            suffix += 1
        used_filenames.add(filename)

        authors = normalize_authors(bib.get("author", ""))
        category = choose_category(pub, bib)
        venue = choose_venue(bib)
        paper_url = choose_paper_url(pub, bib)
        citation = build_citation(authors, title, venue, year)
        markdown = build_markdown(
            title=title,
            permalink_slug=filename[:-3],
            date_str=date_str,
            category=category,
            venue=venue,
            paper_url=paper_url,
            citation=citation,
        )

        target_path = output_dir / filename
        generated_files.append(filename)
        if args.dry_run:
            print(f"[dry-run] would write: {target_path}")
            continue
        target_path.write_text(markdown, encoding="utf-8")
        print(f"Wrote: {target_path}")

    stale_files = set(managed_files)
    if not stale_files:
        for path in output_dir.glob("*.md"):
            if PLACEHOLDER_FILE_RE.match(path.name):
                stale_files.add(path.name)

    for stale_name in sorted(stale_files):
        if stale_name in generated_files:
            continue
        stale_path = output_dir / stale_name
        if not stale_path.exists():
            continue
        if args.dry_run:
            print(f"[dry-run] would delete stale file: {stale_path}")
            continue
        stale_path.unlink()
        print(f"Deleted stale file: {stale_path}")

    if not args.dry_run:
        manifest_path.write_text(
            json.dumps(
                {
                    "source": "google_scholar",
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                    "files": sorted(generated_files),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote manifest: {manifest_path}")

    print(f"Done. Synced {len(generated_files)} publication file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
