"""O*NET data sync script.

Downloads the O*NET database text files, parses them, and loads them into
a local SQLite cache.  Designed to be run standalone:

    python -m app.backend.services.onet.onet_sync

No external dependencies — uses only stdlib modules.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Optional

from app.backend.services.onet.onet_cache import ONETCache

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_ONET_URL = "https://www.onetcenter.org/dl_files/database/db_30_2_text.zip"
DEFAULT_DB_PATH = os.path.join("data", "onet", "db", "onet_cache.db")

# Files we care about inside the ZIP
TARGET_FILES = {
    "Occupation Data.txt",
    "Technology Skills.txt",
    "Alternate Titles.txt",
}


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _download_zip(url: str, timeout: int = 300) -> bytes:
    """Download *url* and return the raw bytes."""
    logger.info("Downloading O*NET data from %s ...", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (ARIA O*NET Sync)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
    logger.info("Download complete: %.2f MB", len(data) / (1024 * 1024))
    return data


def _extract_target_files(zip_bytes: bytes) -> dict[str, io.BytesIO]:
    """Extract the target text files from the ZIP bytes."""
    files: dict[str, io.BytesIO] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            name = info.filename
            # Some ZIPs have a parent directory prefix
            basename = os.path.basename(name)
            if basename in TARGET_FILES:
                logger.info("Extracting %s ...", name)
                files[basename] = io.BytesIO(zf.read(info))
    return files


def _open_text_stream(raw: io.BytesIO) -> io.TextIOWrapper:
    """Open a BytesIO as UTF-8 text, stripping the BOM if present."""
    # Peek at first bytes to detect BOM
    start = raw.read(3)
    raw.seek(0)
    if start == b"\xef\xbb\xbf":
        encoding = "utf-8-sig"
    else:
        encoding = "utf-8"
    return io.TextIOWrapper(raw, encoding=encoding, newline="")


def _parse_occupation_data(reader: csv.reader, cache: ONETCache) -> int:
    """Parse Occupation Data.txt and insert into cache."""
    header = next(reader, None)
    if header is None:
        return 0

    # Map column names to indices (case-insensitive, stripped)
    cols = {h.strip().lower(): i for i, h in enumerate(header)}
    soc_idx = cols.get("o*net-soc code")
    title_idx = cols.get("title")
    desc_idx = cols.get("description")

    if soc_idx is None or title_idx is None:
        logger.warning("Occupation Data.txt missing expected columns")
        return 0

    count = 0
    for row in reader:
        if len(row) <= max(filter(None, [soc_idx, title_idx, desc_idx])):
            continue
        soc = row[soc_idx].strip()
        title = row[title_idx].strip()
        desc = row[desc_idx].strip() if desc_idx is not None else ""
        if soc and title:
            cache.upsert_occupation(soc, title, desc)
            count += 1
    return count


def _parse_technology_skills(reader: csv.reader, cache: ONETCache) -> int:
    """Parse Technology Skills.txt and insert into cache."""
    header = next(reader, None)
    if header is None:
        return 0

    cols = {h.strip().lower(): i for i, h in enumerate(header)}
    soc_idx = cols.get("o*net-soc code")
    example_idx = cols.get("example")
    comm_code_idx = cols.get("commodity code")
    comm_title_idx = cols.get("commodity title")
    hot_idx = cols.get("hot technology")
    demand_idx = cols.get("in demand")

    if soc_idx is None or example_idx is None:
        logger.warning("Technology Skills.txt missing expected columns")
        return 0

    def _yes_no(val: str) -> bool:
        return val.strip().upper() in {"Y", "YES", "TRUE", "1"}

    count = 0
    for row in reader:
        if len(row) <= max(filter(None, [soc_idx, example_idx])):
            continue
        soc = row[soc_idx].strip()
        skill = row[example_idx].strip()
        comm_code = None
        if comm_code_idx is not None and comm_code_idx < len(row):
            try:
                comm_code = int(row[comm_code_idx].strip())
            except ValueError:
                comm_code = None
        comm_title = (
            row[comm_title_idx].strip()
            if comm_title_idx is not None and comm_title_idx < len(row)
            else None
        )
        is_hot = _yes_no(row[hot_idx]) if hot_idx is not None and hot_idx < len(row) else False
        is_demand = (
            _yes_no(row[demand_idx])
            if demand_idx is not None and demand_idx < len(row)
            else False
        )
        if soc and skill:
            cache.upsert_technology_skill(
                soc, skill, comm_code, comm_title, is_hot, is_demand
            )
            count += 1
    return count


def _parse_alternate_titles(reader: csv.reader, cache: ONETCache) -> int:
    """Parse Alternate Titles.txt and insert into cache."""
    header = next(reader, None)
    if header is None:
        return 0

    cols = {h.strip().lower(): i for i, h in enumerate(header)}
    soc_idx = cols.get("o*net-soc code")
    alt_title_idx = cols.get("alternate title")
    short_title_idx = cols.get("short title")

    if soc_idx is None or alt_title_idx is None:
        logger.warning("Alternate Titles.txt missing expected columns")
        return 0

    count = 0
    for row in reader:
        if len(row) <= max(filter(None, [soc_idx, alt_title_idx])):
            continue
        soc = row[soc_idx].strip()
        title = row[alt_title_idx].strip()
        short = (
            row[short_title_idx].strip()
            if short_title_idx is not None and short_title_idx < len(row)
            else None
        )
        if soc and title:
            cache.upsert_alternate_title(soc, title, short or None)
            count += 1
    return count


def sync_onet(
    url: Optional[str] = None,
    db_path: Optional[str] = None,
    skip_download: bool = False,
) -> bool:
    """Download O*NET data and populate the SQLite cache.

    Returns True on success, False on failure.
    """
    url = url or DEFAULT_ONET_URL
    db_path = db_path or DEFAULT_DB_PATH

    _ensure_dir(db_path)
    cache = ONETCache(db_path)

    if skip_download:
        logger.info("Skipping download; using existing cache if present.")
        return cache.is_populated()

    try:
        zip_bytes = _download_zip(url)
    except Exception as e:
        logger.error("Failed to download O*NET data: %s", e)
        return False

    files = _extract_target_files(zip_bytes)
    if not files:
        logger.error("No target files found in the downloaded ZIP.")
        return False

    total_rows = 0
    parsers = {
        "Occupation Data.txt": _parse_occupation_data,
        "Technology Skills.txt": _parse_technology_skills,
        "Alternate Titles.txt": _parse_alternate_titles,
    }

    for filename, parser in parsers.items():
        if filename not in files:
            logger.warning("%s not found in ZIP — skipping", filename)
            continue
        text_stream = _open_text_stream(files[filename])
        reader = csv.reader(text_stream, delimiter="\t")
        count = parser(reader, cache)
        logger.info("Loaded %d rows from %s", count, filename)
        total_rows += count

    cache.set_metadata("version", "30.2")
    cache.set_metadata("download_date", datetime.now(timezone.utc).isoformat())
    cache.set_metadata("file_count", str(len(files)))
    cache.set_metadata("total_rows", str(total_rows))
    cache.commit()

    logger.info(
        "O*NET sync complete — %d total rows written to %s",
        total_rows,
        db_path,
    )
    return True


def main(argv: list[str] = sys.argv[1:]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync O*NET data into local SQLite cache")
    parser.add_argument("--url", default=DEFAULT_ONET_URL, help="O*NET ZIP URL")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Output SQLite path")
    parser.add_argument("--skip-download", action="store_true", help="Skip download")
    args = parser.parse_args(argv)

    ok = sync_onet(url=args.url, db_path=args.db_path, skip_download=args.skip_download)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
