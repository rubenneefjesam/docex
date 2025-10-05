from typing import List
import re


def chunk_text_simple(text: str, size: int = 600, overlap: int = 100) -> List[str]:
    if not text:
        return []
    text = text.strip()
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = start + size
        if end >= L:
            chunks.append(text[start:L].strip())
            break
        slice_ = text[start:end]
        last_space = slice_.rfind(" ")
        if last_space > int(size * 0.6):
            end = start + last_space
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
    return [c for c in chunks if c]


# Simple sentence splitter (naive)
def split_sentences(text: str) -> List[str]:
    # heel basic - voor betere resultaten kun je punkt/tokenizers gebruiken
    return re.split(r"(?<=[.!?])\s+", text)


def chunk_by_sentences(text: str, target_size: int = 600, overlap: int = 100) -> List[str]:
    sents = split_sentences(text)
    chunks = []
    cur = []
    cur_len = 0
    for s in sents:
        if cur_len + len(s) <= target_size or not cur:
            cur.append(s)
            cur_len += len(s)
        else:
            chunks.append(" ".join(cur).strip())
            # start new
            cur = [s]
            cur_len = len(s)
    if cur:
        chunks.append(" ".join(cur).strip())
    # apply overlap (naive: keep last token from previous)
    # For simplicity we rely on chunk_text_simple when needed
    return chunks

