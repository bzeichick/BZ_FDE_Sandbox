"""TC5 Step 4: both implementations on the same requests, four columns each.

  python use_case/evals/measure_ways.py                       # goldens 2, 15, 17 through the pipeline and UTCP
  python use_case/evals/measure_ways.py --goldens 15 --runs 3  # repeat to see how much the numbers move

Model calls and tokens: a LiteLLM callback, the same counter for both implementations, with nothing patched.
Capability calls: a counting wrapper around lookup and extract, passed in the same way as fixture_only.
Seconds: wall clock, end to end, including the TMS calls (through the SSH tunnel in development).
Also: the record bytes fetched, and how many tool calls the model made in its first turn (UTCP only)."""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "01_Product_Engineering" / "challenge"), str(HERE)]
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

import litellm  # noqa: E402

import tms_client  # noqa: E402
from existing_loads import solve_with_lookup  # noqa: E402
from run import fixture_only  # noqa: E402
from schema import Request  # noqa: E402
from utcp_tms import solve_with_utcp  # noqa: E402


class Meter:
    """Counts every model call LiteLLM completes, and its tokens, whichever implementation made it."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = self.tokens_in = self.tokens_out = 0
        self.first_turn_tool_calls = None

    def __call__(self, kwargs, response, start_time, end_time):     # LiteLLM's success-callback signature
        self.calls += 1
        usage = getattr(response, "usage", None)
        if usage:
            self.tokens_in += usage.prompt_tokens or 0
            self.tokens_out += usage.completion_tokens or 0
        if self.first_turn_tool_calls is None:
            self.first_turn_tool_calls = len(getattr(response.choices[0].message, "tool_calls", None) or [])


def settle(meter: Meter, timeout: float = 5.0) -> None:
    """LiteLLM runs success callbacks on a background thread, so wait until the count stops changing."""
    last, end = -1, time.time() + timeout
    while time.time() < end:
        if meter.calls == last and meter.calls > 0:
            return
        last = meter.calls
        time.sleep(0.4)


def counted(fn, tally: dict, key: str, sizes: list | None = None):
    """Count each call of fn (one capability call), and record reply sizes in bytes if asked."""
    def wrapper(arg):
        tally[key] += 1
        out = fn(arg)
        if sizes is not None and isinstance(out, str):
            sizes.append(len(out.encode()))
        return out
    return wrapper


WAYS = {"pipeline": solve_with_lookup, "utcp": solve_with_utcp}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goldens", default="2,15,17", help="golden line numbers, comma-separated")
    parser.add_argument("--runs", type=int, default=1, help="repeat each measurement this many times")
    parser.add_argument("--request", help="a text file holding one order email (e.g. a synthetic request); "
                                          "measured instead of the goldens, expected to need a person")
    parser.add_argument("--received", default="2026-11-09", help="received date for --request")
    args = parser.parse_args()

    meter = Meter()
    litellm.success_callback = [meter]
    goldens = [json.loads(line) for line in open(HERE / "golden.jsonl")]

    if args.request:
        path = Path(args.request)
        cases = [(path.stem, Request(order_text=path.read_text(), received_date=args.received), True)]
    else:
        cases = [(n, Request(**goldens[n - 1]["input"]), goldens[n - 1]["output"]["needs_human"])
                 for n in (int(x) for x in args.goldens.split(","))]

    rows = []
    for n, request, want in cases:
        for way, solve_fn in WAYS.items():
            for _ in range(args.runs):
                tally, sizes = {"lookup": 0, "extract": 0}, []
                lookup = counted(fixture_only(tms_client.lookup), tally, "lookup")   # counts real TMS calls
                extract = counted(tms_client.extract, tally, "extract", sizes)
                meter.reset()
                started = time.perf_counter()
                result = solve_fn(request, lookup, extract)
                seconds = time.perf_counter() - started
                settle(meter)
                rows.append({
                    "golden": n, "way": way, "model calls": meter.calls,
                    "capability calls": f"{tally['lookup'] + tally['extract']} ({tally['lookup']} lookup + {tally['extract']} extract)",
                    "seconds": round(seconds, 1), "tokens": meter.tokens_in + meter.tokens_out,
                    "tokens in": meter.tokens_in, "record bytes fetched": sum(sizes),
                    "1st-turn tool calls": meter.first_turn_tool_calls if way == "utcp" else "-",
                    "right?": "yes" if result.needs_human == want else "NO",
                })

    cols = list(rows[0])
    print("\n| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |")
    for row in rows:
        print("| " + " | ".join(str(row[c]) for c in cols) + " |")


if __name__ == "__main__":
    main()