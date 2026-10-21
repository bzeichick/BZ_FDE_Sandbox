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

import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, computed_field

# All imports live at the top (reviewer feedback): Python's default, and nothing
# here is picked at runtime, which is the one good reason to import inside a function.
from llm import complete

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
# "dry" added in Week 2: operations said every order is "Dry" or "Temp Controlled".
TempMode = Literal["frozen", "refrigerated", "dry"]

# Flags are internal notes for the order desk, not questions for the customer.
# What each one MEANS is written in the `flags` field's description below, not in
# comments here: the model reads descriptions (they go out in the JSON schema)
# but never sees a comment. Add a name here when a real order needs a new one.
Flag = Literal[
    "TEMP_STANDARD_ASSUMED",
    "RATE_LOOKUP_NEEDED",
    "REQUOTE_NEEDED",
    "DELIVERY_TO_BE_SCHEDULED",
    "PICKUP_TO_BE_SCHEDULED",
]

# Operations' own words for the two kinds of order: a "Potential Order" is still
# at the quote stage; a "Valid Order" has an agreed rate (the go signal).
OrderStatus = Literal["potential", "valid"]


class Location(BaseModel):
    """A pickup or delivery place. Every part may be empty — orders often
    give a city but no street, or a company name only."""

    company: str | None = Field(default=None, description="Business name at that place: the shipper, cold storage or consignee.")
    street: str | None = Field(default=None, description="Street address, e.g. '300 E. Lake Dr.'. Empty when only a facility name or city is given.")
    city: str | None = Field(default=None, description="City name.")
    state: str | None = Field(default=None, description="Two-letter US state code, e.g. 'CA'.")
    zip: str | None = Field(default=None, description="5-digit ZIP code, kept as text so leading zeros survive.")


class CustomerQuestion(BaseModel):
    """Something the order doesn't say, phrased as a question to send back."""

    field: str = Field(description="Which Response field is missing, e.g. 'origin' or 'delivery_date'.")
    question: str = Field(description="The question to ask the customer, in plain words.")


class Confirmation(BaseModel):
    """Something we assumed, told to the customer as a statement. Unlike a
    question it needs no reply: the customer only answers if it's wrong."""

    field: str = Field(description="Which Response field was assumed, e.g. 'temp_mode'.")
    statement: str = Field(
        description="What we will do, in plain words, e.g. \"We'll run this frozen at -10°F to 0°F. "
                    "Let us know if that's not right.\""
    )


class FieldChange(BaseModel):
    """A value a later message in the thread changed, e.g. 300 pallets -> 100.
    Kept so the order desk sees what moved instead of only the final number."""

    field: str = Field(description="Which Response field changed, e.g. 'pallets' or 'ready_date'.")
    was: str = Field(description="The earlier value, as written in the thread.")
    now: str = Field(description="The latest value, as written in the thread.")


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
    # Step 12 feedback: a customer's "ready Friday" is not the pickup date. The
    # company picks up on its own consolidated runs, so the customer's date is kept
    # as ready_date and pickup_date is only a firm, scheduled or actual pickup.
    ready_date: date | None = Field(
        default=None,
        description="When the customer says the freight is ready, or the pickup date they request "
                    "('ready as early as Friday', 'requested pick up 9/30 or 10/1' -> the earliest).",
    )
    pickup_date: date | None = Field(
        default=None,
        description="A firm pickup or ship date: one the shipper's documents fix ('ship date October 2') "
                    "or a pickup that already happened. Empty, with PICKUP_TO_BE_SCHEDULED, otherwise.",
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
    # Step 12 feedback: temperature is a range ("zero to negative ten"), not one number.
    temp_mode: TempMode | None = Field(
        default=None,
        description="frozen, refrigerated, or dry (dry freight has no temperature range). "
                    "Empty if the order doesn't say.",
    )
    temp_min_f: float | None = Field(
        default=None,
        description="Coldest allowed temperature in °F, as stated; the company standard is "
                    "frozen -10, refrigerated 34. Empty for dry.",
    )
    temp_max_f: float | None = Field(
        default=None,
        description="Warmest allowed temperature in °F, as stated; the company standard is "
                    "frozen 0, refrigerated 38. Empty for dry.",
    )

    # --- Freight --------------------------------------------------------------
    pallets: int | None = Field(default=None, description="Whole pallets. Every real order so far has been whole numbers.")
    cases: int | None = Field(default=None, description="Total case (carton) count, a whole number.")
    weight_lb: float | None = Field(default=None, description="Total weight in pounds; the gross weight when both gross and net are given.")

    # --- Rate -----------------------------------------------------------------
    # Two fields, because a number in the thread isn't always an agreed price.
    # Only rate_usd goes into the TMS as the charge; quoted_rate_usd is for follow-up.
    rate_usd: float | None = Field(
        default=None,
        description="The AGREED rate in US dollars: accepted by the customer in the thread, the freight "
                    "price on the customer's own PO or freight confirmation, or a rate stated for a load "
                    "already picked up. Empty otherwise.",
    )
    quoted_rate_usd: float | None = Field(
        default=None,
        description="A rate the brokerage quoted that the customer has not accepted yet. Kept so the "
                    "desk can follow up; it is not the agreed rate.",
    )

    # --- Changes in the thread ----------------------------------------------
    changes: list[FieldChange] = Field(
        default_factory=list,
        description="Every value a later message in the thread changed (e.g. pallets 300 -> 100). "
                    "The fields above hold the latest value.",
    )

    # --- What a person needs to know ----------------------------------------
    questions: list[CustomerQuestion] = Field(
        default_factory=list,
        description="One question per required field that the order leaves out.",
    )
    confirmations: list[Confirmation] = Field(
        default_factory=list,
        description="Statements to send the customer about values we assumed (today: a standard "
                    "temperature range). They need no reply, unlike questions.",
    )
    flags: list[Flag] = Field(
        default_factory=list,
        description="Notes for the order desk, never sent to the customer. "
                    "TEMP_STANDARD_ASSUMED: the order said frozen or refrigerated with no number, so the "
                    "company standard range was used. "
                    "RATE_LOOKUP_NEEDED: the thread states no rate at all; look one up or quote. "
                    "REQUOTE_NEEDED: pallets or weight changed after a rate was given, so that rate no "
                    "longer applies. "
                    "DELIVERY_TO_BE_SCHEDULED: no delivery date, or only a vague window; the company "
                    "schedules delivery and advises the customer. "
                    "PICKUP_TO_BE_SCHEDULED: no firm pickup date; the company schedules pickup on its own runs.",
    )

    # The "no answer" switch. Different from an empty field: an empty field
    # means "we got most of it, ask about this piece". needs_human means
    # "don't enter this at all yet — a person has to look".
    needs_human: bool = Field(
        default=False,
        description="True when the text isn't a single new order (e.g. a status update, "
                    "or several shipments) or origin or destination can't be determined.",
    )
    needs_human_reason: str | None = Field(
        default=None,
        description="Why it was handed to a person, in one short sentence.",
    )

    # --- Worked out in code, not by the model ---------------------------------
    # order_status follows from rate_usd alone, so it's computed here rather than
    # asked of the model: the model can't get it wrong or let it disagree with the
    # rate. @computed_field puts it in every JSON reply, but leaves it out of the
    # schema sent to the model, and golden lines that include it still load.
    @computed_field
    @property
    def order_status(self) -> OrderStatus:
        """potential = quote stage, no agreed rate yet. valid = the rate is agreed: the go signal."""
        return "valid" if self.rate_usd is not None else "potential"


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
- Required fields: refs, origin, destination, ready_date or pickup_date, temperature (temp_mode),
  pallets, cases, weight_lb. When one is missing or only partly given, leave the missing part empty and
  add a question for the customer with field set to that field's name. Examples: no case count
  -> field "cases"; origin named only as a facility with no street address -> field "origin";
  no consignee name -> field "destination"; no temperature at all -> field "temp_mode".
- refs: every PO, SO and freight PO number in the order, as written, without labels.
- Dates are YYYY-MM-DD. Resolve relative dates ("Friday") from received_date.
- Pickup: a date the customer gives for when freight is ready, or a pickup date they request, is
  ready_date (if several are offered, use the earliest; "ready as early as Friday" is a ready date).
  The company picks up on its own scheduled runs, so pickup_date is only a firm date fixed by the
  shipper's documents (a ship date) or a pickup that already happened. When there is no firm
  pickup date, leave pickup_date empty and add flag PICKUP_TO_BE_SCHEDULED. If the order gives no
  ready date and no pickup date at all, also ask when it will be ready, with field "ready_date"
  (ask for a ready date, never "when should we pick up").
- Delivery: a specific date is delivery_date. A deadline ("before or on 10/7") is delivery_date.
  A vague window ("week of 10/5") goes in delivery_window as written, delivery_date stays empty,
  and add flag DELIVERY_TO_BE_SCHEDULED. No delivery date at all: leave both empty and add
  DELIVERY_TO_BE_SCHEDULED. Never ask the customer about delivery.
- Temperature is a range. Frozen with "-10" (or "set reefer at -10") is temp_min_f -10,
  temp_max_f 0. A range the order states is used as stated. "REFER" or "reefer" with no other
  temperature word means refrigerated; "REFER (FROZEN)" means frozen. "Dry" or "dry van" is
  temp_mode dry with both temperatures empty. If the order says frozen or refrigerated but
  gives no number, use the company standard (frozen: -10 to 0; refrigerated: 34 to 38), add
  flag TEMP_STANDARD_ASSUMED, and add a confirmation with field "temp_mode" stating the range
  used, e.g. "We'll run this frozen at -10°F to 0°F. Let us know if that's not right." If
  neither mode nor number is stated, or the wording doesn't say which mode (e.g. "ambient"),
  leave all three empty and ask.
- Weight: when both gross and net weight are given, use the gross weight (with pallets).
- Rate: rate_usd is only an AGREED rate: one the customer accepted in the thread, a freight price
  on the customer's own PO or freight confirmation, or a rate stated for a load already picked up.
  A rate the brokerage quoted that the customer hasn't accepted goes in quoted_rate_usd, with
  rate_usd empty. If the thread states no rate at all, leave both empty and add flag
  RATE_LOOKUP_NEEDED. Never ask the customer for a rate.
- Corrections: email threads usually show the newest message first, so go by each message's
  date, not its position. When a later message changes a value (pallets, cases, weight, a date,
  a location, the temperature), use the latest value and add an entry to changes with the field
  name, the earlier value as written (was) and the latest (now). If pallets or weight changed
  AFTER a rate was given, that rate is stale: leave rate_usd and quoted_rate_usd empty and add
  flag REQUOTE_NEEDED instead of RATE_LOOKUP_NEEDED. A rate given after the change is for the new
  count and is used normally.
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
