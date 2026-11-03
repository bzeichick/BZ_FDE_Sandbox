"""Step 5: run the scenarios. Plumbing; the scenarios and their must_not are in scenarios.py.

  uv run python use_case/evals/run_scenarios.py              # checks + scripted user + model user x3
  uv run python use_case/evals/run_scenarios.py --repeats 5

Order, as the course asks:
  1. Oracle agent (a correct draft, built by hand): the simulated users must accept it, or they're broken.
  2. Paraphrasing oracle (same correct drafts, different words): shows what the text check gets wrong.
  3. The real endpoint with the scripted user (deterministic, once).
  4. The real endpoint with a model user (a different model from the endpoint), N repeats -> spread and pass^k.
The worst transcript is saved to use_case/data/scenario_transcript.md (gitignored) for you to read in full.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from helpers import simulation as sim
from scenarios import SCENARIOS, order_agent, render_draft, verified

USER_MODEL = os.getenv("USER_MODEL") or os.getenv("JUDGE_MODEL", "gpt-4.1-mini")


def oracle_state(traj):
    """The correct draft for each scenario at this point in the conversation."""
    from schema import Response
    name = traj.scenario.name
    said = " ".join(t for w, t in traj.turns if w == "user").lower()
    if name.startswith("must do"):
        return Response(refs=["TEST-501"], temp_mode="frozen", temp_min_f=-10, temp_max_f=0, setpoint_f=-10,
                        setpoint_source="stated", pallets=4, pieces=320, piece_unit="CASE", weight_lb=7200,
                        flags=["RATE_LOOKUP_NEEDED"])
    if name.startswith("must ask"):
        if "frozen" in said:
            return Response(refs=["TEST-502"], temp_mode="frozen", temp_min_f=-10, temp_max_f=0, setpoint_f=-10,
                            setpoint_source="stated", pallets=2, pieces=160, piece_unit="CASE", weight_lb=3400)
        return Response(refs=["TEST-502"], pallets=2, pieces=160, piece_unit="CASE", weight_lb=3400,
                        questions=[{"field": "temp_mode", "question": "Should this ship frozen or refrigerated, and at what temperature?"}])
    return Response(needs_human=True, needs_human_reason="Update to an existing PO; a person must change the load in the TMS.")


def make_oracle(paraphrase: bool):
    def agent(traj):
        state = oracle_state(traj)
        traj.states = getattr(traj, "states", []) + [state]
        text = render_draft(state)
        if paraphrase:   # right answer, different words
            text = (text.replace("NEEDS A PERSON:", "Ops review required:").replace("Temp: frozen", "Temperature: frozen")
                        .replace("Question:", "Could you tell us:"))
        return text
    return agent


def row(label, user_label, traj, repeat=""):
    return {"agent": label, "user": user_label, "scenario": traj.scenario.name, "repeat": repeat,
            "state check": int(verified(traj)), "text check": int(sim.text_check(traj)),
            "turns": traj.agent_turns, "ended": traj.ended_because,
            "no repeated questions": int(sim.no_repeated_questions(traj)), "errors": len(traj.errors)}


def table(rows):
    cols = ["agent", "user", "scenario", "repeat", "state check", "text check", "turns", "ended", "no repeated questions", "errors"]
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    out += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--only", help="run the endpoint on scenarios whose name contains this text, e.g. contrast")
    args = ap.parse_args()
    endpoint_scenarios = [sc for sc in SCENARIOS if not args.only or args.only in sc.name]
    model_user = sim.make_llm_user({"model": USER_MODEL})

    print(f"model user: {USER_MODEL}   endpoint: {os.getenv('LLM_MODEL')}\n")
    checks = []
    for label, agent in [("oracle", make_oracle(False)), ("paraphrasing oracle", make_oracle(True))]:
        for user_label, user in [("scripted", sim.scripted_user), ("model", model_user)]:
            for sc in SCENARIOS:
                checks.append(row(label, user_label, sim.simulate(sc, agent, user)))
    print("## Checks before believing anything\n")
    print(table(checks))
    broken = [c for c in checks if c["agent"] == "oracle" and (c["state check"] == 0 or c["ended"] != "goal reached")]
    print("\nOracle accepted by both users: " + ("YES" if not broken else f"NO - {len(broken)} oracle runs failed; fix the user or scenario first"))

    runs, trajs = [], []
    for sc in endpoint_scenarios:
        t = sim.simulate(sc, order_agent, sim.scripted_user)
        runs.append(row("endpoint", "scripted", t)); trajs.append(t)
        for i in range(1, args.repeats + 1):
            t = sim.simulate(sc, order_agent, model_user)
            runs.append(row("endpoint", "model", t, i)); trajs.append(t)
            print(".", end="", flush=True)
    print("\n\n## The endpoint\n")
    print(table(runs))

    print(f"\n## pass^k (model user, state check, {args.repeats} repeats)\n")
    print("| scenario | passed | pass^1 | pass^" + str(args.repeats) + " |\n| --- | --- | --- | --- |")
    for sc in endpoint_scenarios:
        ok = sum(r["state check"] for r in runs if r["scenario"] == sc.name and r["user"] == "model")
        print(f"| {sc.name} | {ok}/{args.repeats} | {sim.pass_k(ok, args.repeats, 1):.2f} | {sim.pass_k(ok, args.repeats, args.repeats):.2f} |")

    def as_md(t, title):
        return (f"# {title} (ended: {t.ended_because}, state check {int(verified(t))})\n\n"
                + "\n\n".join(f"**{who}:**\n```\n{text}\n```" for who, text in t.turns) + "\n")

    worst = next((t for t in trajs if not verified(t)), trajs[0])
    out = ROOT / "use_case" / "data" / "scenario_transcript.md"
    out.write_text(as_md(worst, worst.scenario.name))

    # Every conversation, in run order, so a pass can be checked too (gitignored: the real email is in them).
    folder = ROOT / "use_case" / "data" / "scenario_transcripts"
    folder.mkdir(exist_ok=True)
    for r, t in zip(runs, trajs):
        slug = t.scenario.name.split(":")[0].replace(" ", "_")
        (folder / f"{slug}__{r['user']}{r['repeat']}.md").write_text(as_md(t, f"{t.scenario.name}, {r['user']} user {r['repeat']}"))
    print(f"\nOne transcript to read in full: {out.relative_to(ROOT)}  ({worst.scenario.name})")
    print(f"All {len(trajs)} transcripts: {folder.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
