# chunker.py
import re
from typing import List, Tuple

_ABBREV = {
    "d.w.z.", "m.a.w.", "i.v.m.", "z.o.z.", "m.v.g.", "t.a.v.", "o.a.", "e.d.",
    "etc.", "bv.", "bijv.", "vs.", "mr.", "mw.", "dr.", "prof.", "ir.", "ing."
}

def _is_abbrev(token: str) -> bool:
    t = token.strip().lower()
    return t in _ABBREV or re.fullmatch(r"[a-z]\.", t) is not None  # enkel-letter afkorting zoals "e."

def _split_into_sentences(text: str) -> List[str]:
    if not text:
        return []
    s = text.replace("\r\n", " ").replace("\n", " ").strip()
    if not s:
        return []
    # Split op interpunctie, maar corrigeer simpele afkortingen
    rough = re.split(r"(?<=[\.\?\!…])\s+", s)
    out: List[str] = []
    buf: List[str] = []
    for seg in rough:
        seg = seg.strip()
        if not seg:
            continue
        buf.append(seg)
        # check laatste woord voor afkorting
        last_token = seg.split()[-1] if seg.split() else ""
        if not _is_abbrev(last_token):
            out.append(" ".join(buf).strip())
            buf = []
    if buf:
        out.append(" ".join(buf).strip())
    return out

def _merge_with_lengths(sents: List[str], target_size: int, max_size: int) -> List[str]:
    """Voeg zinnen samen tot target_size, maar forceer hard cap max_size."""
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for s in sents:
        sl = len(s)
        if cur_len == 0 or (cur_len + 1 + sl) <= target_size:
            cur.append(s)
            cur_len += sl + (1 if cur_len else 0)
        else:
            # als huidige + nieuwe > target, push huidige
            joined = " ".join(cur).strip()
            if joined:
                chunks.append(joined[:max_size].strip())
            cur = [s]
            cur_len = sl
        # guard: nooit > max_size laten groeien
        if cur_len > max_size:
            joined = " ".join(cur).strip()
            if joined:
                chunks.append(joined[:max_size].strip())
            cur, cur_len = [], 0
    if cur:
        joined = " ".join(cur).strip()
        if joined:
            chunks.append(joined[:max_size].strip())
    return chunks

def _add_overlap(chunks: List[str], overlap: int) -> List[str]:
    """Voeg karakter-overlap toe tussen opeenvolgende chunks."""
    if overlap <= 0 or not chunks:
        return chunks
    if len(chunks) == 1:
        return chunks
    out = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = out[-1][-overlap:]
        # probeer op woordgrens te plakken
        merged = (prev_tail + " " + chunks[i]).strip()
        out.append(merged)
    return out

def chunk_text_simple(text: str, size: int = 600, overlap: int = 100) -> List[str]:
    if not text:
        return []
    text = text.strip()
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + size, L)
        slice_ = text[start:end]
        if end < L:
            last_space = slice_.rfind(" ")
            if last_space > int(size * 0.6):
                end = start + last_space
        chunks.append(text[start:end].strip())
        start = end if overlap <= 0 else max(end - overlap, end)
    return [c for c in chunks if c]

def chunk_by_sentences(
    text: str,
    target_size: int = 600,
    overlap: int = 100,
    max_size: int = 1000
) -> List[str]:
    sents = _split_into_sentences(text)
    if not sents:
        return chunk_text_simple(text, size=target_size, overlap=overlap)
    base = _merge_with_lengths(sents, target_size=target_size, max_size=max_size)
    if overlap and overlap > 0:
        return _add_overlap(base, overlap=min(overlap, target_size // 2))
    return base
