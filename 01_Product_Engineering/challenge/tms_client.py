"""Thin client for the TMS's XML web service: one HTTPS POST endpoint, stdlib only.

Settings come from the repo-root .env (never committed): TMS_HOST, TMS_PATH, TMS_USER, TMS_PASS.
Every request and reply is saved under use_case/data/tms_wire/ (gitignored), so reply sizes can be
measured (TC5 Step 5) and failures read afterwards. Shared by seed_sandbox.py and the UTCP adapter."""
import base64
import os
import re
import socket
from contextlib import contextmanager
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

_PARENTS = Path(__file__).resolve().parents
ROOT = _PARENTS[2] if len(_PARENTS) > 2 else _PARENTS[0]   # the repo root locally; /app inside the Docker image
WIRE = ROOT / "use_case" / "data" / "tms_wire"
SETTINGS = ("TMS_HOST", "TMS_PATH", "TMS_USER", "TMS_PASS")


class TMSError(RuntimeError):
    """A call that failed: HTTP error, bad login or caller IP, or a failure inside the reply."""


def configured() -> bool:
    """True when every setting is present. Docker and classmates won't have them (mock fallback later)."""
    return all(os.getenv(k) for k in SETTINGS)


def _decode(data: str) -> str:
    """Replies are base64 unless the server was set otherwise. Plain oids are left as they are."""
    if re.fullmatch(r"[0-9,\s]*", data):
        return data
    try:
        text = base64.b64decode(data, validate=True).decode("utf-8")
    except Exception:
        return data
    printable = sum(ch.isprintable() or ch in "\r\n\t" for ch in text)
    return text if text and printable / len(text) > 0.95 else data


@contextmanager
def _ipv4_only():
    """The TMS allows callers by IPv4 address. On a network with IPv6, Python would otherwise
    connect over IPv6 and be refused ("Access denied from IP address: 2601:..."). Only DNS lookups
    made inside this block are limited to IPv4; everything else in the process is untouched afterwards."""
    real = socket.getaddrinfo
    socket.getaddrinfo = lambda *a, **k: [r for r in real(*a, **k) if r[0] == socket.AF_INET]
    try:
        yield
    finally:
        socket.getaddrinfo = real


def _open(request, timeout):
    """Open the request directly, or through an SSH tunnel when TMS_SOCKS=host:port is set.

    The tunnel (ssh -N -D 1080 <server>) sends only the TMS calls out from a server whose IP the TMS
    allows. DNS is resolved on the server too (rdns=True), so the call goes out over its IPv4."""
    proxy = os.getenv("TMS_SOCKS")
    if not proxy:
        with _ipv4_only():
            return urllib.request.urlopen(request, timeout=timeout)
    import socks
    from sockshandler import SocksiPyHandler
    host, port = proxy.rsplit(":", 1)
    handler = SocksiPyHandler(socks.SOCKS5, host, int(port), rdns=True)
    return urllib.request.build_opener(handler).open(request, timeout=timeout)


def call(service_id: str, data_xml: str, timeout: int = 60) -> str:
    """One request to the service. Returns the decoded <data>; raises TMSError on any failure."""
    if not configured():
        raise TMSError("set TMS_HOST, TMS_PATH, TMS_USER and TMS_PASS in .env")
    rid = time.strftime("%Y%m%d%H%M%S") + "-" + os.urandom(3).hex()
    request = (f"<service-request><service-id>{escape(service_id)}</service-id>"
               f"<request-id>{rid}</request-id><data>{data_xml}</data></service-request>")
    host = re.sub(r"^https?://", "", os.environ["TMS_HOST"]).rstrip("/")
    url = f"https://{host}{os.environ['TMS_PATH']}"
    body = urllib.parse.urlencode({"userid": os.environ["TMS_USER"], "password": os.environ["TMS_PASS"],
                                   "request": request}).encode()
    WIRE.mkdir(parents=True, exist_ok=True)
    stem = WIRE / f"{rid}_{service_id}"
    Path(f"{stem}.request.xml").write_text(request)
    try:
        with _open(urllib.request.Request(url, data=body, method="POST"), timeout) as r:
            status, text = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
    except OSError as e:      # unreachable, refused or timed out (e.g. the tunnel is down): still a TMS failure
        raise TMSError(f"TMS unreachable: {e}") from e
    Path(f"{stem}.response.xml").write_text(text)
    if status != 200:
        hint = {403: ": bad login, user not authorized, or this computer's IP isn't allowed",
                503: ": too many requests at once, retry"}.get(status, "")
        raise TMSError(f"HTTP {status}{hint}")
    root = ET.fromstring(text)
    if (root.findtext("status/code") or "").upper() not in ("", "SUCCESS"):
        raise TMSError(f"{root.findtext('status/code')}: {root.findtext('status/message') or root.findtext('error') or ''}")
    node = root.find("data")
    if node is not None and len(node):                    # XML placed directly inside <data>
        decoded = "".join(ET.tostring(child, encoding="unicode") for child in node)
    else:
        decoded = _decode((root.findtext("data") or "").strip())
    Path(f"{stem}.decoded.xml").write_text(decoded)
    # An import can answer SUCCESS and still have failed: the failure is inside <Logs>.
    if "<Logs>" in decoded and re.search(r"<Severity>(SEVERE|ERROR)</Severity>|<Message>FAIL", decoded):
        raise TMSError(f"import failed, see {stem}.decoded.xml")
    return decoded


def lookup(value: str, search_by: str = "reference") -> list[str]:
    """Shipment oids whose reference matches `value` exactly ([] if none)."""
    out = call("OidLookup", f"<objectType>shipment</objectType><searchBy>{escape(search_by)}</searchBy>"
                            f"<searchValue>{escape(value)}</searchValue>")
    return re.findall(r"\d{6,}", out or "")


def extract(oid: str) -> str:
    """The whole shipment record as XML: the reply whose size Step 5 measures."""
    return call("WebExtractShipment", f"<oid>{escape(oid)}</oid>")


def import_order(xml: str, file_stem: str) -> str:
    """Create or update one shipment from an import document (the seeding script uses this)."""
    xml = re.sub(r"^\s*<\?xml[^>]*\?>", "", xml)
    name = f"{file_stem}_{int(time.time())}.xml"           # must be unique per call
    data = (f"<WebImport><WebImportHeader><FileName>{escape(name)}</FileName><Type>WebImportShipmentV2</Type>"
            f"<UserName>{escape(os.environ['TMS_USER'])}</UserName></WebImportHeader>"
            f"<WebImportFile>{xml}</WebImportFile></WebImport>")
    return call("ImportWeb", data)


def summarize(xml: str) -> dict:
    """The few fields of a shipment record that the checks use (about 300 bytes instead of about 10 KB).
    Tolerant of layout: a field that isn't found stays None."""
    root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", xml))
    ship = next((e for e in root.iter() if e.tag.split("}")[-1] == "Shipment"), root)

    def text(path):
        el = ship.find(path)
        return (el.text or "").strip() or None if el is not None else None

    def day(path):                                   # "06/25/2026 07:00" -> "2026-06-25"
        v = text(path)
        return f"{v[6:10]}-{v[0:2]}-{v[3:5]}" if v and len(v) >= 10 else None

    refs = {r.get("type"): (r.text or "").strip() for r in ship.findall("ReferenceNumbers/ReferenceNumber")}
    out = {"shipment_id": refs.pop("Shipment ID", None), "refs": refs, "status": text("Status"),
           "pickup": day("Dates/Pickup/Date"), "delivery": day("Dates/Drop/Date"),
           "origin_zip": text("Shipper/Address/PostalCode"), "dest_zip": text("Consignee/Address/PostalCode"),
           "temp_min_f": None, "temp_max_f": None, "pallets": None, "weight_lb": None}
    for el in ship.iter():
        tag = el.tag.split("}")[-1]
        val = (el.text or "").strip()
        if tag == "MinTemperature" and val and out["temp_min_f"] is None:
            out["temp_min_f"] = float(val)
        elif tag == "MaxTemperature" and val and out["temp_max_f"] is None:
            out["temp_max_f"] = float(val)
        elif tag == "Quantity" and "PALLET" in (el.get("uom") or "").upper() and val and out["pallets"] is None:
            out["pallets"] = float(val)
        elif tag == "Weight" and val and out["weight_lb"] is None:
            out["weight_lb"] = float(val)
    return out