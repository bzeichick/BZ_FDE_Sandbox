"""Implementation 2 (TC5): the TMS's own lookup service, described in a UTCP manifest
(tms_utcp_manifest.json) and called by the model as tools. Compared against implementation 1,
the pipeline (existing_loads.solve_with_lookup), on the same goldens."""
import json
from pathlib import Path

try:
    from helpers.tools import Toolbox  # the course's dispatcher: a tool failure is a message, never an exception
except ImportError:
    from tools import Toolbox          # the copy shipped in the Docker image (helpers/ isn't in it)

MANIFEST = json.loads(Path(__file__).with_name("tms_utcp_manifest.json").read_text())


def utcp_schemas(manifest: dict) -> list[dict]:
    """The manifest already says everything a tool schema says, so derive it (Session 10's shape)."""
    return [{
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": {
                "type": "object",
                "properties": {name: {"type": spec["type"], "description": spec.get("description", "")}
                               for name, spec in tool["inputs"].items()},
                "required": [name for name, spec in tool["inputs"].items() if spec.get("required")],
            },
        },
    } for tool in manifest["tools"]]


def make_toolbox(lookup, extract, log: dict) -> Toolbox:
    """The manifest's two tools, wired to the injected lookup/extract, so the real TMS client, the eval's
    fixture filter or Step 4's counter all plug in the same way as for the pipeline.

    log["tried"] collects every reference the model looked up, so the after-check doesn't repeat them.
    log["failures"] collects TMS failures: Toolbox still hands each one to the model as a message, but the
    caller reads this list afterwards and sends the order to a person (Decision 2)."""
    from tms_client import TMSError
    schemas = {s["function"]["name"]: s for s in utcp_schemas(MANIFEST)}
    box = Toolbox(max_result_chars=20_000)      # Decision 1: the default 4,000 would cut a 10 KB record to 40%

    def find_shipment_by_reference(reference: str) -> list[str]:
        log["tried"].add(reference)
        try:
            oids = lookup(reference)
            if oids:
                log["found"][reference] = oids   # the after-check counts these even if the model ignores them
            return oids
        except TMSError as error:
            log["failures"].append(f"find_shipment_by_reference({reference}): {error}")
            raise                               # Toolbox turns it into a message for the model

    def get_shipment(oid: str) -> str:
        try:
            return extract(oid)
        except TMSError as error:
            log["failures"].append(f"get_shipment({oid}): {error}")
            raise

    box.register(find_shipment_by_reference, schema=schemas["find_shipment_by_reference"])
    box.register(get_shipment, schema=schemas["get_shipment"])
    return box


TOOL_RULES = """

TOOLS: before deciding this is a new order, look up its reference numbers (PO, SO, BOL, load, confirmation,
appointment) with find_shipment_by_reference. If one matches, read it with get_shipment. If the order is about
a load already in the TMS, it is not a new order: set needs_human, name the load in needs_human_reason, and list
what the email changes in changes. When you have finished looking things up, reply with the JSON only.

"""


def solve_with_utcp(request, lookup, extract, meter=None, max_rounds: int = 8):
    """Implementation 2: the same rules and contract as solve(), but the model looks loads up itself through
    the manifest's tools. Then the same after-check as the pipeline. A TMS failure during the loop sends the
    order to a person (Decision 2), whatever the model concluded."""
    from litellm import completion
    from pydantic import ValidationError

    from existing_loads import TMS_DOWN, _escalate, after_check, candidates
    from llm import MODEL, NUM_RETRIES, TIMEOUT_S, _provider_kwargs
    from schema import INTAKE_RULES, Response
    from tms_client import TMSError

    log = {"tried": set(), "found": {}, "failures": []}
    box = make_toolbox(lookup, extract, log)
    messages = [
        {"role": "system", "content": INTAKE_RULES + TOOL_RULES + json.dumps(Response.model_json_schema())},
        {"role": "user", "content": f"received_date: {request.received_date.isoformat()}\n\nORDER:\n{request.order_text}"},
    ]
    draft = None
    for _ in range(max_rounds):
        reply = completion(model=MODEL, messages=messages, tools=box.schemas, temperature=0, drop_params=True,
                           timeout=TIMEOUT_S, num_retries=NUM_RETRIES, **_provider_kwargs())
        usage = getattr(reply, "usage", None)
        if usage:
            print(f"[tokens] model={MODEL} in={usage.prompt_tokens} out={usage.completion_tokens} (utcp)", flush=True)
        if meter:
            meter.track(reply)
        msg = reply.choices[0].message
        if getattr(msg, "tool_calls", None):
            messages += box.run(msg)            # the assistant turn plus one result per call; never raises
            continue
        content = msg.content or ""
        try:
            draft = Response.model_validate_json(content[content.find("{"): content.rfind("}") + 1])
            break
        except ValidationError as error:
            messages += [{"role": "assistant", "content": content},
                         {"role": "user", "content": f"Your answer did not match the schema: {str(error)[:1500]}\n"
                                                     "Return corrected JSON only."}]
    if draft is None:
        draft = Response(needs_human=True, needs_human_reason="Couldn't read this order reliably; please enter it by hand.")
    if log["failures"]:
        return _escalate(draft, TMS_DOWN)

    matches = [{"oid": oid, "matched_ref": ref, "shipment_id": None}
               for ref, oids in log["found"].items() for oid in oids]
    tried = set(log["tried"])        # exactly what the model looked up: its tool doesn't apply REF_RULES
    try:
        return after_check(draft, tried, matches, lookup, extract)
    except TMSError:
        return _escalate(draft, TMS_DOWN)