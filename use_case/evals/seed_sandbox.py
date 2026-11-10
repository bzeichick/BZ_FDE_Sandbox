"""Seed the TMS sandbox with the loads the golden emails refer to (use_case/evals/tms_fixture.json).

  uv run python use_case/evals/seed_sandbox.py           # dry run: print each import document, send nothing
  uv run python use_case/evals/seed_sandbox.py --send    # create or update the loads, then look each one up
  uv run python use_case/evals/seed_sandbox.py --check   # look each load up by every ref (changes nothing)

Safety: refuses unless the enterprise name contains SANDBOX, every Intake ID starts CL-FDE- and every ref
starts ZZFDE. Create-only: a load whose Intake ID already exists is skipped. To change one, give it a new Intake ID.
Needs the TMS settings in .env, plus TMS_SOCKS with the tunnel open when calls go through the server.
The vendor's document wrapper is in use_case/data/tms_import_template.xml (gitignored)."""
import argparse
import json
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "01_Product_Engineering" / "challenge"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")
import tms_client  # noqa: E402

FIXTURE = HERE / "tms_fixture.json"
TEMPLATE = ROOT / "use_case" / "data" / "tms_import_template.xml"
LEDGER = ROOT / "use_case" / "data" / "fde_sandbox_ledger.json"
NOTE = "TEST LOAD - DO NOT TENDER - FDE COURSE"


def _date(iso: str, hhmm: str) -> str:
    y, m, d = iso.split("-")
    return f"{m}/{d}/{y} {hhmm}"


def _address(tag: str, a: dict) -> str:
    parts = [("Name", a["name"]), ("AddrLine1", a["street"]), ("City", a["city"]),
             ("StateProvince", a["state"]), ("PostalCode", a["zip"])]
    inner = "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in parts if v) + "<CountryCode>USA</CountryCode>"
    return f"<{tag}><Address>{inner}</Address></{tag}>"


def body(load: dict, enterprise: str) -> str:
    """One load as the inside of an import document, in the same shape the production pipeline sends."""
    refs = [("Intake ID", load["intake_id"]), *map(tuple, load["refs"]),
            ("Actual Pallets", load["pallets"]), ("Cases", load["cases"])]
    ref_xml = (f'<ReferenceNumber isPrimary="true" type="Shipment ID">{escape(load["intake_id"])}</ReferenceNumber>'
               + "".join(f'<ReferenceNumber isPrimary="false" type="{escape(t)}">{escape(str(v))}</ReferenceNumber>'
                         for t, v in refs if v is not None))
    temp = ""
    if load.get("temp_min_f") is not None:
        temp = (f"<MinTemperature>{load['temp_min_f']}</MinTemperature>"
                f"<MaxTemperature>{load['temp_max_f']}</MaxTemperature><TemperatureUnits>F</TemperatureUnits>")
    return (f'<Enterprise customerAcctNum="{escape(enterprise)}" name="{escape(enterprise)}"/>'
            f"<ReferenceNumbers>{ref_xml}</ReferenceNumbers>"
            f'<Comments><Comment type="SpecialInstructions">{NOTE} (golden {load["golden"]})</Comment></Comments>'
            f'<Dates><Pickup><Date type="earliest">{_date(load["pickup"], "08:00")}</Date>'
            f'<Date type="latest">{_date(load["pickup"], "14:00")}</Date></Pickup>'
            f'<Drop><Date type="earliest">{_date(load["delivery"], "07:00")}</Date>'
            f'<Date type="latest">{_date(load["delivery"], "15:00")}</Date></Drop></Dates>'
            + _address("Shipper", load["shipper"]) + _address("Consignee", load["consignee"])
            + '<ItemGroups><ItemGroup id="1" isHandlingUnit="false" isShipUnit="false" sequence="1">'
            f'<LineItem lineNumber="1"></LineItem><Description>{escape(load["description"])}</Description>{temp}'
            '<FreightClasses><FreightClass type="ordered">70</FreightClass></FreightClasses>'
            f'<Weights><Weight type="planned" uom="lb">{load["weight_lb"]}</Weight></Weights>'
            f'<Quantities><Quantity type="planned" uom="PALLET SPOT(S)">{load["pallets"]}</Quantity></Quantities>'
            "<HazardousMaterial>false</HazardousMaterial></ItemGroup></ItemGroups>"
            "<Payment><Method>Prepaid</Method></Payment><Status>Pending</Status>")


def check_safe(loads: list, enterprise: str) -> None:
    if "SANDBOX" not in enterprise.upper():
        sys.exit(f"refusing: '{enterprise}' is not a sandbox enterprise")
    for load in loads:
        if not load["intake_id"].startswith("CL-FDE-"):
            sys.exit(f"refusing: Intake ID {load['intake_id']} must start CL-FDE-")
        bad = [v for _, v in load["refs"] if not str(v).startswith("ZZFDE")]
        if bad:
            sys.exit(f"refusing: golden {load['golden']} refs {bad} must start ZZFDE")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--send", action="store_true", help="create or update the loads in the sandbox")
    mode.add_argument("--check", action="store_true", help="look every load up by every ref; changes nothing")
    args = parser.parse_args()

    loads = json.loads(FIXTURE.read_text())["loads"]
    enterprise = os.getenv("TMS_SANDBOX_ENTERPRISE") or sys.exit("set TMS_SANDBOX_ENTERPRISE in .env")
    check_safe(loads, enterprise)
    if not TEMPLATE.exists():
        sys.exit(f"missing {TEMPLATE.relative_to(ROOT)} (the vendor's document wrapper; gitignored)")
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}

    for load in loads:
        iid = load["intake_id"]
        if args.check:
            for ref in [iid, *(v for _, v in load["refs"])]:
                print(f"  golden {load['golden']}  {ref:16} -> {tms_client.lookup(ref) or 'NOT FOUND'}")
            continue
        existing = tms_client.lookup(iid) if args.send else []
        if existing:   # create-only: the TMS rejects an update unless it repeats the bill-to set at creation
            print(f"  golden {load['golden']}  {iid}  -> {existing} (already there; skipped)")
            ledger[iid] = {"golden": load["golden"], "oids": existing}
            continue
        doc = TEMPLATE.read_text().replace("{body}", body(load, enterprise))
        if not args.send:
            print(f"--- golden {load['golden']} ({iid}), {len(doc)} bytes\n{doc}\n")
            continue
        tms_client.import_order(doc, iid)
        oids = tms_client.lookup(iid)
        ledger[iid] = {"golden": load["golden"], "oids": oids}
        print(f"  golden {load['golden']}  {iid}  -> {oids or 'sent, but not found yet'}")

    if args.send:
        LEDGER.write_text(json.dumps(ledger, indent=1))
    elif not args.check:
        print("dry run: nothing sent. Add --send to create the loads.")


if __name__ == "__main__":
    main()