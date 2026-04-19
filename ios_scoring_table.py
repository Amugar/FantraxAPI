"""
Fantrax League Scoring Table for Pythonista (iOS)

FIRST RUN: leave DIAGNOSTIC = True. The script will print the raw API
response structure. Paste that output in the chat so the code can be
updated to match Fantrax's current response format, then set
DIAGNOSTIC = False to get the actual table.
"""
from __future__ import annotations
import sys, os, traceback, json

_here = os.path.dirname(os.path.abspath(__file__))

# ── Force local fantraxapi over any installed site-packages version ───────────
for _k in list(sys.modules):
    if _k == "fantraxapi" or _k.startswith("fantraxapi."):
        del sys.modules[_k]
while _here in sys.path:
    sys.path.remove(_here)
sys.path.insert(0, _here)

# ── Config ────────────────────────────────────────────────────────────────────
LEAGUE_ID  = "w41gbc9xmm422zxu"
DIAGNOSTIC = True   # set False once the table is working
# ─────────────────────────────────────────────────────────────────────────────

import requests as _req


def _show_env():
    local = os.path.join(_here, "fantraxapi")
    print(f"Script dir      : {_here}")
    print(f"Local pkg found : {os.path.isdir(local)}")
    try:
        import fantraxapi as _fa
        print(f"Loaded pkg from : {os.path.dirname(_fa.__file__)}")
    except Exception as e:
        print(f"Import error    : {e}")


def _api_call(methods: list[dict]) -> list[dict]:
    sess = _req.Session()
    body = {"msgs": [{"method": m["method"], "data": {**m.get("data", {}), "leagueId": LEAGUE_ID}} for m in methods]}
    r = sess.post("https://www.fantrax.com/fxpa/req",
                  params={"leagueId": LEAGUE_ID}, json=body, timeout=20)
    r.raise_for_status()
    return [resp["data"] for resp in r.json()["responses"]]


def run_diagnostic():
    """Print the raw API response structure so we can fix league.py."""
    print("\n=== DIAGNOSTIC MODE ===")
    _show_env()

    print("\nCalling Fantrax init API …")
    methods = [
        {"method": "getFantasyLeagueInfo"},
        {"method": "getRefObject",      "data": {"type": "FantasyItemStatus"}},
        {"method": "getLiveScoringStats","data": {"newView": "True"}},
        {"method": "getTeamRosterInfo", "data": {"view": "GAMES_PER_POS"}},
        {"method": "getTeamRosterInfo", "data": {"view": "STATS"}},
    ]
    labels = [
        "getFantasyLeagueInfo",
        "getRefObject(FantasyItemStatus)",
        "getLiveScoringStats",
        "getTeamRosterInfo(GAMES_PER_POS)",
        "getTeamRosterInfo(STATS)",
    ]

    try:
        responses = _api_call(methods)
    except Exception as e:
        print(f"API call failed: {e}")
        traceback.print_exc()
        return

    print("\n--- Response key structure (copy everything below) ---")
    for i, (data, label) in enumerate(zip(responses, labels)):
        print(f"\n[{i}] {label}")
        print(f"  top-level keys: {sorted(data.keys())}")
        for k, v in sorted(data.items()):
            if isinstance(v, dict):
                print(f"    {k} (dict) keys: {sorted(v.keys())}")
            elif isinstance(v, list) and v:
                sample = v[0]
                if isinstance(sample, dict):
                    print(f"    {k} (list[dict]) first-item keys: {sorted(sample.keys())}")
                else:
                    print(f"    {k} (list): first item = {repr(sample)[:80]}")
    print("\n--- End of diagnostic output ---")


# ── Table helpers ─────────────────────────────────────────────────────────────

def _col_widths(headers, rows):
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    return widths


def print_table(headers, rows, title=""):
    widths = _col_widths(headers, rows)
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "|" + "|".join(" {:<" + str(w) + "} " for w in widths) + "|"
    if title:
        print(f"\n{'=' * len(sep)}\n{title}\n{'=' * len(sep)}")
    print(sep)
    print(fmt.format(*[str(h) for h in headers]))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))
    print(sep)


# ── Main table logic ──────────────────────────────────────────────────────────

def build_period_table(league):
    print("\nFetching scoring period results …")
    periods = league.scoring_period_results()
    print(f"Found {len(periods)} periods.")

    sorted_nums = sorted(periods.keys())
    scores = {t.id: {} for t in league.teams}
    for pnum, result in sorted(periods.items()):
        for m in result.matchups:
            if hasattr(m.away, "id"):
                scores[m.away.id][pnum] = m.away_score
            if hasattr(m.home, "id"):
                scores[m.home.id][pnum] = m.home_score

    headers = ["Team"] + [f"P{p}" for p in sorted_nums] + ["Total"]
    rows = []
    for team in sorted(league.teams, key=lambda t: t.name):
        ps = [scores.get(team.id, {}).get(p, "-") for p in sorted_nums]
        total = sum(s for s in ps if isinstance(s, float))
        rows.append([team.name] + [f"{s:.1f}" if isinstance(s, float) else s for s in ps] + [f"{total:.1f}"])
    print_table(headers, rows, title="SCORING SUMMARY BY PERIOD")


def build_roster_tables(league):
    print("\nFetching rosters …")
    for team in sorted(league.teams, key=lambda t: t.name):
        try:
            roster = league.team_roster(team.id)
        except Exception as e:
            print(f"  [!] {team.name}: {e}")
            continue
        headers = ["Pos", "Player", "Pts/G", "Total Pts"]
        rows = []
        for row in roster.rows:
            name  = row.player.name if row.player else "— Empty —"
            ppg   = f"{row.fantasy_points_per_game:.1f}" if row.fantasy_points_per_game is not None else "-"
            total = f"{row.total_fantasy_points:.1f}"   if row.total_fantasy_points  is not None else "-"
            rows.append([row.position.short_name, name, ppg, total])
        print_table(headers, rows, title=f"ROSTER: {team.name}")


def main():
    if DIAGNOSTIC:
        run_diagnostic()
        return

    try:
        from fantraxapi import League
        import fantraxapi as _fa
        print(f"fantraxapi from : {os.path.dirname(_fa.__file__)}")
        print("Connecting …")
        league = League(LEAGUE_ID)
        print(f"League : {league.name}  |  Season : {league.year}  |  Teams : {len(league.teams)}")
        build_period_table(league)
        build_roster_tables(league)
        print("\nDone.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
