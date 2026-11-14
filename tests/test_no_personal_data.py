"""No personal data from the setup this project was generalized from may appear in the repository.

The forbidden terms are stored only as truncated SHA-256 fingerprints, so this
test doesn't itself leak them. Every text file is split into lowercase word
n-grams (1-5 words), and each n-gram is hashed and compared.
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINGERPRINTS = {
    "04c4866b2df0b867", "0dcdad31f168fcb2", "0e6b1d211a808d2a", "4384d8fcad02d738", "4ae6af4d07e4656f",
    "4d5b19a4c81591f3", "588689d0b0be56f9", "6eb8de7e4a112431", "7f5960cd8e067dfa", "900fc3ec8970b44c",
    "a25b62ab9ed26ecb", "f15d2b1e1a487d65", "f3605818637babe0", "f58b9791137e27b6",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "dist"}
TEXT_EXT = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".tmpl", ".cfg", ".csv", ""}


def _files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) and p.suffix.lower() in TEXT_EXT:
            yield p


def _hits(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    found = set()
    for n in range(1, 6):
        for i in range(len(words) - n + 1):
            h = hashlib.sha256(" ".join(words[i:i + n]).encode()).hexdigest()[:16]
            if h in FINGERPRINTS:
                found.add(" ".join(words[i:i + n]))
    return found


def test_repository_contains_no_personal_data():
    leaks = {}
    for f in _files():
        hits = _hits(f.read_text(encoding="utf-8", errors="ignore"))
        if hits:
            leaks[str(f.relative_to(ROOT))] = len(hits)  # don't echo the terms themselves
    assert not leaks, f"personal data fingerprints found in: {leaks}"


def test_fingerprint_matcher_works():
    probe = hashlib.sha256(b"hello world").hexdigest()[:16]
    FINGERPRINTS.add(probe)
    try:
        assert _hits("Hello, World!") == {"hello world"}
    finally:
        FINGERPRINTS.discard(probe)
