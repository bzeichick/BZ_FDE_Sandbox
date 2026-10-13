"""The contract for ColdLade order intake: what goes in, what comes out.

This file is the In -> Out row of use_case/CHARTER.md, written as types.
If the charter and this file ever disagree, one of them is wrong — change
the charter first, then this file.

How to read it (pydantic basics):
  - Each class is a shape. Each line inside is one field: `name: type`.
  - A field with NO default (no `= ...`) is REQUIRED: the caller must provide it.
  - `X | None = None` means "may be empty". Most shipment fields are like this,
    because the charter says: leave it empty rather than guess.
  - Field(description=...) is documentation. It is read by people now, and
    later by the model and by agents picking this as a tool (Week 5).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# What goes in
# ---------------------------------------------------------------------------

class Request(BaseModel):
    """One customer order, as the order desk received it."""

    # Required: there is nothing to do without the order itself.
    order_text: str = Field(
        min_length=1,
        description="The full text of ONE order: the email body, with any attached "
                    "PDFs (PO, freight confirmation) converted to text and pasted below it."
    )

    # Required: turns relative dates ("pick up Friday") into real calendar dates.
    received_date: date = Field(
        description="The date the order was received, used to resolve relative "
                    "dates like 'Friday' or 'next week'."
    )


# ---------------------------------------------------------------------------
# Building blocks used inside the Response
# ---------------------------------------------------------------------------

# A Literal is a list of the ONLY values allowed. Anything else is rejected.
TempMode = Literal["frozen", "refrigerated"]

# Flags are internal notes for the order desk, not questions for the customer.
# Start small; add a name here when a real order needs a new one.
Flag = Literal[
    "TEMP_STANDARD_ASSUMED",  # order said frozen/refrigerated but no number; company standard range used — confirm
    "RATE_LOOKUP_NEEDED",     # no rate in the order; needs a rate lookup or a quote
    "DELIVERY_TO_BE_SCHEDULED",  # no delivery date given; the company schedules it and advises the customer
]


class Location(BaseModel):
    """A pickup or delivery place. Every part may be empty — orders often
    give a city but no street, or a company name only."""

    company: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, description="Two-letter US state code, e.g. 'CA'.")
    zip: str | None = Field(default=None, description="5-digit ZIP code, kept as text so leading zeros survive.")


class CustomerQuestion(BaseModel):
    """Something the order doesn't say, phrased as a question to send back."""

    field: str = Field(description="Which Response field is missing, e.g. 'origin' or 'delivery_date'.")
    question: str = Field(description="The question to ask the customer, in plain words.")


# ---------------------------------------------------------------------------
# What comes out
# ---------------------------------------------------------------------------

class Response(BaseModel):
    """The shipment fields read from the order, ready for a person to check.

    Rule for every field below: use only what the order text says. Never fill
    a value from what a customer usually does. If it isn't stated, leave it
    empty and add a CustomerQuestion (except rate — see flags).
    """

    # --- References ---------------------------------------------------------
    # A list, because one order can carry several (PO, SO, freight PO).
    # `default_factory=list` means "empty list if none were found".
    refs: list[str] = Field(
        default_factory=list,
        description="Every customer reference number in the order (PO, SO, freight PO), as written.",
    )

    # --- Where ----------------------------------------------------------------
    origin: Location | None = Field(default=None, description="Pickup location. Empty if the order doesn't name one.")
    destination: Location | None = Field(default=None, description="Delivery location.")

    # --- When -----------------------------------------------------------------
    pickup_date: date | None = Field(
        default=None,
        description="A specific pickup day. Empty if not stated or too vague to pin down.",
    )
    delivery_date: date | None = Field(
        default=None,
        description="A specific delivery day, or the deadline for 'on or before' wording. "
                    "Empty for vague windows like 'week of 10/5' (kept in delivery_window instead). "
                    "Empty with the DELIVERY_TO_BE_SCHEDULED flag when the order gives no delivery date at all.",
    )

    delivery_window: str | None = Field(
        default=None,
        description="The customer's delivery wording as written when it is not a single date or "
                    "deadline, e.g. 'week of 10/5'. The company schedules within it.",
    )

    # --- Temperature ----------------------------------------------------------
    temp_mode: TempMode | None = None
    temp_max_f: float | None = Field(
        default=None,
        description="Warmest allowed temperature in °F (e.g. 'set reefer -10F' -> -10).",
    )

    # --- Freight --------------------------------------------------------------
    pallets: int | None = Field(default=None, description="Whole pallets. Every real order so far has been whole numbers.")
    cases: int | None = None
    weight_lb: float | None = Field(default=None, description="Total weight in pounds.")
    rate_usd: float | None = Field(default=None, description="Agreed rate in US dollars, if the order states one.")

    # --- What a person needs to know ----------------------------------------
    questions: list[CustomerQuestion] = Field(
        default_factory=list,
        description="One question per required field that the order leaves out.",
    )
    flags: list[Flag] = Field(default_factory=list)

    # The "no answer" switch. Different from an empty field: an empty field
    # means "we got most of it, ask about this piece". needs_human means
    # "don't enter this at all yet — a person has to look".
    needs_human: bool = Field(
        default=False,
        description="True when the text isn't a single new order (e.g. a status update, "
                    "or several shipments) or origin, destination or pickup date can't be determined.",
    )
    needs_human_reason: str | None = Field(
        default=None,
        description="Why it was handed to a person, in one short sentence.",
    )


# ---------------------------------------------------------------------------
# The whole product, as one function
# ---------------------------------------------------------------------------

# The rules from the charter's In -> Out row, written for the model. When the
# charter changes, this text changes with it. Field meanings come from the
# Field(description=...) text above, which is sent along as a JSON schema.
INTAKE_RULES = """You read ONE customer shipping order for a cold-chain freight brokerage and fill in
the shipment fields for the order desk to check before entering it into the TMS.

Return ONLY a JSON object matching the JSON schema below. No prose, no code fences.

Rules:
- Use only what the order text says (body, subject line, attachments). Never fill a value
  from what a customer usually does, and never invent one. Empty (null) beats a guess.
- Required fields: refs, origin, destination, pickup_date, temperature (temp_mode), pallets,
  cases, weight_lb. When one is missing or only partly given, leave the missing part empty and
  add a question for the customer with field set to that field's name. Examples: no case count
  -> field "cases"; origin named only as a facility with no street address -> field "origin";
  no consignee name -> field "destination"; no temperature at all -> field "temp_mode".
- refs: every PO, SO and freight PO number in the order, as written, without labels.
- Dates are YYYY-MM-DD. Resolve relative dates ("Friday") from received_date. If several pickup
  dates are offered, use the earliest. "As early as <day>" is the pickup date.
- Delivery: a specific date is delivery_date. A deadline ("before or on 10/7") is delivery_date.
  A vague window ("week of 10/5") goes in delivery_window as written, delivery_date stays empty,
  and add flag DELIVERY_TO_BE_SCHEDULED. No delivery date at all: leave both empty and add
  DELIVERY_TO_BE_SCHEDULED. Never ask the customer about delivery.
- Temperature: "-10" or "-10F" with frozen means temp_max_f -10. If the order says frozen or
  refrigerated but gives no number, use the company standard (frozen: temp_max_f 0;
  refrigerated: temp_max_f 38) and add flag TEMP_STANDARD_ASSUMED. If neither mode nor number
  is stated, leave both empty and ask.
- Weight: when both gross and net weight are given, use the gross weight (with pallets).
- Rate: a rate stated anywhere in the thread (a quoted rate, a PO price) goes in rate_usd. If no
  rate is stated, leave it empty and add flag RATE_LOOKUP_NEEDED. Never ask the customer for a rate.
- Quote requests are treated as orders: fill the fields the same way.
- needs_human is true only when (a) the text is not a single new order -- for example the latest
  message says the shipment was already picked up or delivered, or it covers several shipments --
  or (b) the origin or destination cannot be determined at all. Even then, fill in everything the
  order does state and add the questions. Give needs_human_reason in one short sentence.

JSON schema:
"""


def solve(request: Request) -> Response:
    """Read one customer order and return its shipment fields for a person to check.

    A fixed pipeline (see use_case/decisions.md): one model call, check the reply
    against Response, retry once with the error if it doesn't fit, and hand it to a
    person if it still doesn't. It never returns something that fails the contract.
    """
    import json

    from pydantic import ValidationError

    # Imported here, not at the top, so `import schema` stays light: Week 2's data
    # generation needs these types without loading the model client.
    from llm import complete

    system = INTAKE_RULES + json.dumps(Response.model_json_schema())
    message = f"received_date: {request.received_date.isoformat()}\n\nORDER:\n{request.order_text}"

    last_error = None
    for attempt in range(2):
        if last_error:
            message += f"\n\nYour previous answer did not match the schema: {last_error}\nReturn corrected JSON only."
        reply = complete(message, system=system)
        # Models sometimes wrap JSON in ``` fences or add a sentence; keep only the {...} part.
        text = reply[reply.find("{"): reply.rfind("}") + 1]
        try:
            return Response.model_validate_json(text)
        except ValidationError as error:
            last_error = str(error)[:1500]

    return Response(
        needs_human=True,
        needs_human_reason="Couldn't read this order reliably; please enter it by hand.",
    )
