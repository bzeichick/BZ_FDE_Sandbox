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
# The whole product, as one function signature
# ---------------------------------------------------------------------------

def solve(request: Request) -> Response:
    """Read one customer order and return its shipment fields for a person to check.

    Built in Step 8. Until then it deliberately does nothing.
    """
    raise NotImplementedError("implement against this signature")
