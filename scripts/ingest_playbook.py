from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from app.db.session import SessionLocal
from app.services.repositories import PlaybookRepo

ALLOWED_EXT = {'.txt', '.md', '.json', '.csv', '.html'}
MESSAGES_PART_RE = re.compile(r'^messages(\d*)\.html$', re.IGNORECASE)
MESSAGE_DIV_RE = re.compile(r'<div class="message[^\"]*"[^>]*>(.*?)</div>\s*</div>', re.DOTALL)
FROM_RE = re.compile(r'<div class="from_name">(.*?)</div>', re.DOTALL)
TEXT_RE = re.compile(r'<div class="text">(.*?)</div>', re.DOTALL)
BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\n{3,}')


def chunk_text(text: str, chunk_size: int = 1600, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk.strip())
        i += max(1, chunk_size - overlap)
    return chunks


def infer_source_type(path: Path) -> str:
    p = str(path).lower()
    if 'script' in p or 'playbook' in p:
        return 'script'
    return 'chat'


def html_to_text(raw: str) -> str:
    raw = BR_RE.sub('\n', raw)
    raw = TAG_RE.sub('', raw)
    raw = html.unescape(raw)
    raw = raw.replace('\xa0', ' ')
    lines = [line.strip() for line in raw.splitlines()]
    return '\n'.join([line for line in lines if line]).strip()


def parse_telegram_messages_html(content: str) -> str:
    rows: list[str] = []

    # Prefer Telegram-like message blocks if available.
    for block in MESSAGE_DIV_RE.findall(content):
        text_match = TEXT_RE.search(block)
        if not text_match:
            continue
        message_text = html_to_text(text_match.group(1))
        if not message_text:
            continue
        from_match = FROM_RE.search(block)
        from_name = html_to_text(from_match.group(1)) if from_match else ''
        if from_name:
            rows.append(f'{from_name}: {message_text}')
        else:
            rows.append(message_text)

    if rows:
        return '\n'.join(rows)

    # Fallback: strip all tags if markup differs.
    fallback = html_to_text(content)
    return WS_RE.sub('\n\n', fallback)


def source_name_for(path: Path, root: Path) -> str:
    if MESSAGES_PART_RE.match(path.name):
        parent = path.parent.name
        rel = path.parent.relative_to(root)
        return f'tg_export/{rel.as_posix()} ({parent})'
    return path.name


def messages_part_index(path: Path) -> int | None:
    m = MESSAGES_PART_RE.match(path.name)
    if not m:
        return None
    # messages.html -> 1, messages2.html -> 2, etc.
    suffix = m.group(1)
    return int(suffix) if suffix else 1


def main() -> None:
    parser = argparse.ArgumentParser(description='Import scripts/chats into playbook snippets')
    parser.add_argument('--dir', required=True, help='Directory with scripts and chat exports')
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists() or not root.is_dir():
        raise SystemExit('Invalid directory')

    db = SessionLocal()
    repo = PlaybookRepo(db)
    inserted = 0
    parsed_html_files = 0
    try:
        all_files = [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ALLOWED_EXT]

        # 1) Import non-message files as before.
        message_parts = [p for p in all_files if messages_part_index(p) is not None]
        for path in all_files:
            if path in message_parts:
                continue

            raw = path.read_text(encoding='utf-8', errors='ignore')
            content = raw
            if path.suffix.lower() == '.html':
                content = parse_telegram_messages_html(raw)
                parsed_html_files += 1

            if not content.strip():
                continue

            for chunk in chunk_text(content):
                repo.add_snippet(
                    source_type=infer_source_type(path),
                    source_name=source_name_for(path, root),
                    content=chunk,
                )
                inserted += 1

        # 2) Group and concatenate messages*.html per export folder.
        grouped: dict[Path, list[Path]] = {}
        for path in message_parts:
            grouped.setdefault(path.parent, []).append(path)

        for folder, parts in grouped.items():
            ordered = sorted(parts, key=lambda p: messages_part_index(p) or 99999)
            parsed_parts: list[str] = []
            for part in ordered:
                raw = part.read_text(encoding='utf-8', errors='ignore')
                parsed = parse_telegram_messages_html(raw)
                if parsed.strip():
                    parsed_parts.append(parsed)
                parsed_html_files += 1

            combined = '\n'.join(parsed_parts).strip()
            if not combined:
                continue

            source_path = folder / 'messages.html'
            for chunk in chunk_text(combined):
                repo.add_snippet(
                    source_type='chat',
                    source_name=source_name_for(source_path, root),
                    content=chunk,
                )
                inserted += 1

        print(f'imported snippets: {inserted}')
        print(f'parsed html files: {parsed_html_files}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
