"""Embed every record once, for technique 3 (hybrid). Run again whenever corpus.py changes.

    uv run --env-file ../../.env python embed.py        # production if COLDLADE_DB is set, else synthetic

Saves <name>.npy (one vector per record) and <name>.json (record IDs, model, measured token count).
Production files go in use_case/data/ (gitignored): the vectors are derived from real orders.
"""

import json
from datetime import datetime

import numpy as np

import retrieval


def main() -> None:
    records, _ = retrieval.corpus()
    texts = [retrieval.embed_text(r) for r in records]
    path = retrieval.embed_path()
    print(f"Embedding {len(texts):,} records with {retrieval.EMBED_MODEL} "
          f"(first {retrieval.EMBED_CHARS:,} characters each) -> {path}.npy")
    vectors, tokens = retrieval.embed_texts(texts, progress=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path.with_suffix(".npy"), vectors)
    path.with_suffix(".json").write_text(json.dumps({
        "model": retrieval.EMBED_MODEL, "records": len(texts), "chars_cap": retrieval.EMBED_CHARS,
        "tokens": tokens, "date": f"{datetime.now():%Y-%m-%d %H:%M}",
        "fingerprint": retrieval.fingerprint(texts),   # what was embedded; checked before every use
        "ids": [r.id for r in records],
    }))
    print(f"Done: {len(texts):,} vectors, {tokens:,} tokens (measured, as reported by the API).")


if __name__ == "__main__":
    main()