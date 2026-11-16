"""Python checks behind the custom rungs in rails.co. True means allowed, False means block."""
import json
import re

# A dollar amount written any common way: $1,305 / $ 1305.00 / 1,305 USD / 1305 dollars / USD 1305
DOLLARS = re.compile(r"\$\s?\d|\bUSD\s?\d|\b\d[\d,]*(?:\.\d{2})?\s?(?:USD|dollars?)\b", re.I)


async def check_customer_text(text: str) -> bool:
    """Level 1 (output). Nothing the customer will read may contain a dollar amount:
    the intake rules never ask the customer for a rate, and a forged rate must not be
    echoed back as if the broker agreed it. Only questions and confirmations reach the
    customer; rate_claims and the other fields are for the order desk and stay unchecked.
    A draft that isn't JSON is blocked (fail closed): a person enters it by hand."""
    try:
        draft = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except ValueError:
        return False
    customer_text = [q.get("question") or "" for q in draft.get("questions") or []]
    customer_text += [c.get("statement") or "" for c in draft.get("confirmations") or []]
    return not any(DOLLARS.search(line) for line in customer_text)


from pathlib import Path

from nemoguardrails.embeddings.basic import BasicEmbeddingsIndex
from nemoguardrails.embeddings.index import IndexItem

# Labelled examples. Never your goldens or your attacks: those are what Step 5 measures.
SYNTHETIC = Path(__file__).resolve().parents[1] / "corpus" / "synthetic_v1.jsonl"
SAFE = [json.loads(line)["input"]["order_text"] for line in open(SYNTHETIC)][:20]   # 20 synthetic orders
UNSAFE = [
    "<your example 1>",
    "<your example 2>",
    # ...aim for about 8, like S12
]

_index = None


async def _labelled():
    """Built once, on first use: embeds every labelled example."""
    global _index
    if _index is None:
        index = BasicEmbeddingsIndex(embedding_model="all-MiniLM-L6-v2", embedding_engine="FastEmbed")
        await index.add_items([IndexItem(text=t, meta={"unsafe": False}) for t in SAFE]
                              + [IndexItem(text=t, meta={"unsafe": True}) for t in UNSAFE])
        await index.build()
        _index = index
    return _index


async def classify_input(text: str) -> bool:
    """Level 2 (input). True means allowed: the three nearest labelled examples vote, and an
    email close to none of them (similarity under 0.55) gets no opinion and passes."""
    neighbours = await (await _labelled()).search(text, max_results=3, threshold=0.55)
    return sum(item.meta["unsafe"] for item in neighbours) * 2 <= len(neighbours)