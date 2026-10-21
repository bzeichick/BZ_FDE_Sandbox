"""The model call.

One function, one job: take a conversation, stream back the assistant's reply.

Everything provider-specific lives in environment variables, so switching from
OpenAI to Azure to a self-hosted model is a config change, not a code change.
That property matters more than it looks like it does right now -- see the
"Where does this live?" section of the README.
"""

import json
import os

from litellm import completion, token_counter

# LiteLLM picks the provider from the model string:
#   "gpt-4.1-mini"                    -> OpenAI
#   "azure/my-deployment"             -> Azure OpenAI
#   "anthropic/claude-sonnet-5"       -> Anthropic
#   "ollama/llama3.2"                 -> a model running on your laptop
#   "openai/my-model" + LLM_API_BASE  -> any OpenAI-compatible server (vLLM, LM Studio, ...)
MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
API_BASE = os.getenv("LLM_API_BASE")  # only needed for self-hosted / gateway endpoints
EXTRA_HEADERS = json.loads(os.getenv("LLM_EXTRA_HEADERS") or "{}")

# Give up on a model call after 60 s and retry twice, so a slow or down provider
# returns an error the page can show instead of hanging until Nginx times out.
TIMEOUT_S = 60
NUM_RETRIES = 2

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful assistant. Be concise and concrete.",
)


def _build_messages(message: str, history: list[dict] | None = None,
                    system: str | None = None) -> list[dict]:
    """The exact message list sent to the model: system prompt, past turns, new message.

    Shared by every function below, so the token count, the chat, and the
    order-intake call can never drift apart on what actually goes over the wire.
    """
    messages = [{"role": "system", "content": system or SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": message})
    return messages


def _provider_kwargs() -> dict:
    """Optional settings for gateways and self-hosted models. Empty for plain OpenAI/Anthropic."""
    kwargs = {}
    if API_BASE:
        kwargs["api_base"] = API_BASE
    if EXTRA_HEADERS:
        kwargs["extra_headers"] = EXTRA_HEADERS
    return kwargs


def count_prompt_tokens(message: str, history: list[dict] | None = None) -> int:
    """Count how many tokens the next request would send, before sending it.

    Builds the same message list `stream_reply` would send, so the count
    reflects what actually goes over the wire -- not just the new message.
    """
    return token_counter(model=MODEL, messages=_build_messages(message, history))


def stream_reply(message: str, history: list[dict] | None = None):
    """Yield the assistant's reply as it arrives, one growing string at a time.

    `history` is a list of {"role": ..., "content": ...} dicts. We rebuild the
    full message list on every turn -- the model is stateless, so the
    conversation only exists because we keep sending it.
    """
    reply = ""
    # LiteLLM's completion() is typed as returning one of several objects (a stream,
    # a full reply, or an async one), so the checker can't see that stream=True means
    # a stream. `type: ignore` covers that library quirk only.
    for chunk in completion(model=MODEL, messages=_build_messages(message, history),  # type: ignore
                            stream=True, timeout=TIMEOUT_S, num_retries=NUM_RETRIES,
                            **_provider_kwargs()):
        piece = chunk.choices[0].delta.content
        if piece:
            reply += piece
            yield reply


def complete(message: str, system: str, history: list[dict] | None = None) -> str:
    """Return the model's whole reply at once (no streaming).

    For structured answers like the order-intake JSON: half a JSON object is
    useless to the caller, so there is nothing to gain from streaming it.
    temperature=0 makes the same order give the same answer as often as possible,
    which is what lets us compare runs against the goldens. Some models (Claude
    Sonnet 5, for one) only accept their default temperature; drop_params=True tells
    LiteLLM to quietly leave out any setting the chosen model doesn't support,
    instead of failing the whole call.
    """
    response = completion(model=MODEL, messages=_build_messages(message, history, system),
                          temperature=0, drop_params=True, timeout=TIMEOUT_S,
                          num_retries=NUM_RETRIES, **_provider_kwargs())
    # Print what each call actually used, so cost per order is measured, not guessed (Step 13).
    usage = getattr(response, "usage", None)
    if usage:
        print(f"[tokens] model={MODEL} in={usage.prompt_tokens} out={usage.completion_tokens}", flush=True)
    # Same LiteLLM typing quirk as above: without stream=True this is a full reply.
    return response.choices[0].message.content or ""  # type: ignore
