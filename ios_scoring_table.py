"""
Fantrax League Scoring Table for Pythonista (iOS)

Setup on Pythonista:
  1. Copy the entire FantraxAPI folder to your Pythonista documents.
  2. Open this file and tap Run.

The script prints:
  - Period-by-period scoring summary (all teams vs all periods)
  - Current roster for every team with per-player point totals
"""
from __future__ import annotations

import sys
import os

# Put the repo root at the front of sys.path so the local fantraxapi
# package is used even if an older version is installed in site-packages.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

# Evict any already-cached fantraxapi modules (e.g. from site-packages)
# so the import below always picks up the local patched version.
for _key in list(sys.modules.keys()):
    if _key == "fantraxapi" or _key.startswith("fantraxapi."):
        del sys.modules[_key]

from requests import Session
from fantraxapi import League

# ── Configuration ────────────────────────────────────────────────────────────
LEAGUE_ID = "w41gbc9xmm422zxu"
USERNAME  = "Turdy"
PASSWORD  = "Jacklyn1864!!!"
# ─────────────────────────────────────────────────────────────────────────────


def fantrax_login(username: str, password: str) -> Session:
    """Return an authenticated requests Session using direct HTTP login."""
    session = Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ),
    })

    # Fetch the login page first so the session picks up any CSRF cookies.
    session.get("https://www.fantrax.com/home", timeout=15)

    login_url = "https://www.fantrax.com/newuser!login.go"
    payload = {
        "username":   username,
        "password":   password,
        "rememberMe": "Y",
    }
    resp = session.post(login_url, data=payload, allow_redirects=True, timeout=15)

    if resp.status_code >= 400:
        raise RuntimeError(f"Login request failed with HTTP {resp.status_code}")

    # Fantrax sets a session cookie on success; a missing cookie means failure.
    if not any(c.name.lower().startswith("fantrax") for c in session.cookies):
        raise RuntimeError("Login succeeded HTTP-wise but no Fantrax session cookie was set.")

    return session


def _col_widths(headers: list, rows: list) -> list:
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    return widths


def print_table(headers: list, rows: list, title: str = "") -> None:
    widths = _col_widths(headers, rows)
    sep    = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt    = "|" + "|".join(" {:<" + str(w) + "} " for w in widths) + "|"

    if title:
        print(f"\n{'=' * len(sep)}")
        print(title)
        print("=" * len(sep))
    print(sep)
    print(fmt.format(*[str(h) for h in headers]))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))
    print(sep)


def build_period_table(league: League) -> None:
    """Print a team × period scoring grid from matchup data."""
    print("\nFetching scoring period results …")
    periods = league.scoring_period_results()

    sorted_period_nums = sorted(periods.keys())

    # Map every team_id → {period_num: score}
    scores: dict = {t.id: {} for t in league.teams}
    for pnum, result in sorted(periods.items()):
        for matchup in result.matchups:
            if hasattr(matchup.away, "id"):
                scores[matchup.away.id][pnum] = matchup.away_score
            if hasattr(matchup.home, "id"):
                scores[matchup.home.id][pnum] = matchup.home_score

    headers = ["Team"] + [f"P{p}" for p in sorted_period_nums] + ["Total"]
    rows = []
    for team in sorted(league.teams, key=lambda t: t.name):
        period_scores = [scores.get(team.id, {}).get(p, "-") for p in sorted_period_nums]
        total = sum(s for s in period_scores if isinstance(s, float))
        row = [team.name]
        for s in period_scores:
            row.append(f"{s:.1f}" if isinstance(s, float) else s)
        row.append(f"{total:.1f}")
        rows.append(row)

    print_table(headers, rows, title="SCORING SUMMARY BY PERIOD")


def build_roster_tables(league: League) -> None:
    """Print each team's current roster with per-player fantasy point totals."""
    print("\nFetching rosters …")
    for team in sorted(league.teams, key=lambda t: t.name):
        try:
            roster = league.team_roster(team.id)
        except Exception as exc:
            print(f"\n  [!] Could not fetch roster for {team.name}: {exc}")
            continue

        headers = ["Pos", "Player", "Pts/G", "Total Pts"]
        rows = []
        for row in roster.rows:
            player_name = row.player.name if row.player else "— Empty —"
            ppg   = f"{row.fantasy_points_per_game:.1f}" if row.fantasy_points_per_game is not None else "-"
            total = f"{row.total_fantasy_points:.1f}"   if row.total_fantasy_points  is not None else "-"
            rows.append([row.position.short_name, player_name, ppg, total])

        print_table(headers, rows, title=f"ROSTER: {team.name}")


def main() -> None:
    print("Connecting to Fantrax …")

    session: Session | None = None
    try:
        session = fantrax_login(USERNAME, PASSWORD)
        print(f"Logged in as {USERNAME}")
    except Exception as exc:
        print(f"Login failed ({exc}) — continuing without authentication.")

    league = League(LEAGUE_ID, session=session)
    print(f"\nLeague : {league.name}")
    print(f"Season : {league.year}")
    print(f"Teams  : {len(league.teams)}")

    build_period_table(league)
    build_roster_tables(league)

    print("\nDone.")


if __name__ == "__main__":
    main()
