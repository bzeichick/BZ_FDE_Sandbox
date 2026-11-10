"""A stand-in for the TMS, built from tms_fixture.json: the same lookup/extract shapes as tms_client,
with no network and no credentials. Used when the TMS settings aren't present (the Docker image, a
classmate's machine), so both TC5 implementations still run end to end on the course's four loads."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from tms_client import TMSError

_HERE = Path(__file__).resolve().parent
_CANDIDATES = [_HERE / "tms_fixture.json"]                                  # the copy shipped in the image
if len(_HERE.parents) > 1:                                                  # locally: the course's own copy too
    _CANDIDATES.append(_HERE.parents[1] / "use_case" / "evals" / "tms_fixture.json")
_FIXTURE = next(p for p in _CANDIDATES if p.exists())
LOADS = {load["intake_id"]: load for load in json.loads(_FIXTURE.read_text())["loads"]}


def lookup(value: str, search_by: str = "reference") -> list[str]:
    """Exact match, like the real lookup. Intake IDs stand in for the TMS's oids."""
    return [iid for iid, load in LOADS.items() if value == iid or value in [v for _, v in load["refs"]]]


def _day(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{m}/{d}/{y} 08:00"


def extract(oid: str) -> str:
    """A small record in the TMS's layout, enough for summarize() (a real one is 8.5-10 KB)."""
    if oid not in LOADS:
        raise TMSError(f"no shipment {oid}")
    load = LOADS[oid]
    refs = "".join(f'<ReferenceNumber type="{escape(t)}">{escape(v)}</ReferenceNumber>'
                   for t, v in [("Shipment ID", oid), *load["refs"]])
    temp = ("" if load["temp_min_f"] is None else
            f"<MinTemperature>{load['temp_min_f']}</MinTemperature><MaxTemperature>{load['temp_max_f']}</MaxTemperature>")
    return (f"<Shipment><ReferenceNumbers>{refs}</ReferenceNumbers><Status>Pending</Status>"
            f"<Dates><Pickup><Date>{_day(load['pickup'])}</Date></Pickup><Drop><Date>{_day(load['delivery'])}</Date></Drop></Dates>"
            f"<Shipper><Address><PostalCode>{load['shipper']['zip']}</PostalCode></Address></Shipper>"
            f"<Consignee><Address><PostalCode>{load['consignee']['zip']}</PostalCode></Address></Consignee>"
            f"<ItemGroups><ItemGroup>{temp}<Weights><Weight>{load['weight_lb']}</Weight></Weights>"
            f'<Quantities><Quantity uom="PALLET SPOT(S)">{load["pallets"]}</Quantity></Quantities></ItemGroup></ItemGroups></Shipment>')