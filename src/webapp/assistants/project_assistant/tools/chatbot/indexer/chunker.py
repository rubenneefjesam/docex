# chunker.py
import re
from typing import List

def chunk_text_simple(text: str, size: int = 600, overlap: int = 100) -> List[str]:
    """Sliding-window chunker (char-based but keep words intact)."""
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

def _split_into_sentences(text: str) -> List[str]:
    # naive sentence splitter
    if not text:
        return []
    # keep punctuation as sentence boundary
    splits = re.split(r'(?<=[\.\?\!…])\s+', text.replace("\r\n", " ").replace("\n", " "))
    return [s.strip() for s in splits if s.strip()]

def chunk_by_sentences(text: str, target_size: int = 600, overlap: int = 100) -> List[str]:
    """Group sentences until near target_size to create semantically coherent chunks."""
    sents = _split_into_sentences(text)
    if not sents:
        return chunk_text_simple(text, size=target_size, overlap=overlap)
    chunks = []
    cur = []
    cur_len = 0
    for s in sents:
        slen = len(s)
        if cur_len + slen <= target_size or not cur:
            cur.append(s)
            cur_len += slen + 1
        else:
            chunks.append(" ".join(cur).strip())
            # start new
            cur = [s]
            cur_len = slen + 1
    if cur:
        chunks.append(" ".join(cur).strip())
    # optional: overlap by taking last sentence(s) into next chunk
    return chunks
