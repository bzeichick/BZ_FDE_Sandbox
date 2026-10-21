"""The server.

`gradio.Server` is a FastAPI app with Gradio's API engine bolted in. You get
queueing, streaming, and MCP for free, but you bring your own frontend. That
split is the point: the API is the product, the UI is disposable.
"""

import os
from pathlib import Path

from fastapi.responses import HTMLResponse
from gradio import Server
from pydantic import ValidationError

from llm import stream_reply
from schema import Request, Response, solve

app = Server()

FRONTEND = Path(__file__).parent / "frontend" / "index.html"


# --- The API -----------------------------------------------------------------
# The `-> str` return annotation is REQUIRED. Without it Gradio infers zero
# output components and silently returns nothing. Ask us how we know.


# `chat` streams (yields) its reply, so a type checker expects a generator type,
# but Gradio needs `-> str` to know the endpoint returns text. Gradio wins; the
# two `type: ignore`s silence that one known mismatch and nothing else.
@app.api(name="chat")
def chat(message: str, history: list | None = None) -> str:  # type: ignore
    """Stream a reply to one user message."""
    yield from stream_reply(message, history)  # type: ignore


@app.api(name="draft_shipment_from_order")
def draft_shipment_from_order(order_text: str, received_date: str) -> str:
    """Read one customer shipping order and draft the shipment for the TMS.

    order_text: the full text of ONE order -- email body, with any PO or freight
    confirmation PDFs converted to text and pasted below it.
    received_date: the date the order arrived, YYYY-MM-DD (resolves "pick up Friday").

    Returns a JSON object (the Response in schema.py): refs, origin, destination,
    ready, pickup and delivery dates, temperature, pallets, cases, weight; the agreed
    rate and any rate quoted but not yet accepted; order_status (potential or valid);
    values a later message changed; questions to send the customer for anything
    missing, and confirmations (no reply needed) for anything assumed; flags for the
    order desk; and needs_human=true when the order should not be entered without a
    person checking.
    Never guesses: anything the order doesn't state is left empty.
    """
    try:
        # model_validate takes the raw text and lets pydantic turn "2026-10-21" into a
        # date (or reject it). Same check as Request(...), but the type checker no
        # longer reads it as passing text where a date belongs.
        request = Request.model_validate({"order_text": order_text, "received_date": received_date})
    except ValidationError:
        # A bad date or empty input is answered in the same shape, not with a crash,
        # so every caller -- the web page, the eval harness, an agent -- handles one format.
        return Response(
            needs_human=True,
            needs_human_reason="The order text or received date was missing or not a valid date (use YYYY-MM-DD).",
        ).model_dump_json()
    return solve(request).model_dump_json()


# --- The frontend ------------------------------------------------------------
# Defining a route at "/" replaces Gradio's default UI with ours.


@app.get("/", response_class=HTMLResponse)
def homepage() -> str:
    return FRONTEND.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    """Your future ops team will thank you. Load balancers need this."""
    return {"status": "ok", "model": os.getenv("LLM_MODEL", "gpt-4.1-mini")}


if __name__ == "__main__":
    # 0.0.0.0 so the container is reachable from the host. On your laptop this
    # is fine. On a firm network, "reachable from where, exactly?" is the
    # question this challenge wants you to go ask.
    #
    # Read the port rather than hardcoding it, so a machine that already has
    # something on 7860 can move this one without editing code.
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))

    # Gradio announces the address it BOUND to, which is 0.0.0.0 -- not an
    # address a browser can open. Windows rejects it outright; macOS and Linux
    # quietly redirect it to localhost, which is why it looks fine on some
    # machines and broken on others. Print the one that always works.
    print(f"\n  Open http://localhost:{port} in your browser\n", flush=True)
    app.launch(server_name="0.0.0.0", server_port=port)
