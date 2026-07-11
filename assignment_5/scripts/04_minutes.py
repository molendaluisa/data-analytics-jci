import os
import json
import pandas as pd

CACHE_EVENTS = "assignment_5/cache/events"
CACHE_LINEUPS = "assignment_5/cache/lineups"

# --- Step 1: Derive each match's real period lengths from events ---
# P1 clock runs 0:00 -> ~47:00 (incl. stoppage); P2 restarts at 45:00 -> ~95:00.
period_ends = {}  # match_id -> {1: end_seconds, 2: end_seconds} (clock time)
for f in os.listdir(CACHE_EVENTS):
    ev = pd.read_parquet(f"{CACHE_EVENTS}/{f}",
                         columns=["match_id", "period", "minute", "second"])
    ev["clock_sec"] = ev["minute"] * 60 + ev["second"]
    ends = ev.groupby("period")["clock_sec"].max().to_dict()
    period_ends[ev["match_id"].iloc[0]] = ends

# --- Step 2: Helper -- convert "MM:SS" clock strings to seconds ---
def to_sec(clock_str):
    m, s = clock_str.split(":")
    return int(m) * 60 + int(s)

# --- Step 3: Helper -- convert a (clock_sec, period) pair to one absolute timeline ---
# P1 occupies [0, p1_end]; P2 clock restarts at 45:00, so we append it after p1_end.
def to_abs(clock_sec, period, p1_end):
    if period == 1:
        return clock_sec
    return p1_end + (clock_sec - 45 * 60)

# --- Step 4: Loop over lineups; per player, take the UNION of stint intervals ---
# (Position changes can be logged as overlapping intervals -- summing them
#  double-counts. Merging intervals makes the calculation overlap-proof.)
rows = []
for f in os.listdir(CACHE_LINEUPS):
    lu = pd.read_parquet(f"{CACHE_LINEUPS}/{f}")
    mid = lu["match_id"].iloc[0]
    ends = period_ends[mid]
    p1_end = ends.get(1, 45 * 60)
    p2_end_abs = to_abs(ends.get(2, 90 * 60), 2, p1_end)

    for _, r in lu.iterrows():
        positions = json.loads(r["positions"]) if isinstance(r["positions"], str) else []

        # --- Step 4a: Convert every stint to an absolute (start, end) interval ---
        intervals = []
        for st in positions:
            start = to_abs(to_sec(st["from"]), st.get("from_period", 1), p1_end)
            if st.get("to") is None:
                end = p2_end_abs          # played until the final whistle
            else:
                end = to_abs(to_sec(st["to"]),
                             st.get("to_period", st.get("from_period", 1)),
                             p1_end)
            if end > start:
                intervals.append((start, end))

        # --- Step 4b: Merge overlapping intervals (the fix for double-counting) ---
        intervals.sort()
        merged = []
        for s, e in intervals:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        total = sum(e - s for s, e in merged)

        if total > 0:
            rows.append({"match_id": mid,
                         "player_id": r["player_id"],
                         "player": r["player_name"],
                         "team": r["team_name"],
                         "minutes": round(total / 60, 1)})

# --- Step 5: Save the player-match minutes table ---
minutes = pd.DataFrame(rows)
minutes.to_parquet("assignment_5/models/player_match_minutes.parquet", index=False)
print(f"Player-match rows: {len(minutes):,}")

# --- Check 1: Invariant -- no player exceeds her own match's length ---
match_len = {m: to_abs(e.get(2, 90 * 60), 2, e.get(1, 45 * 60)) / 60
             for m, e in period_ends.items()}
minutes["match_len"] = minutes["match_id"].map(match_len)
bad = minutes[minutes["minutes"] > minutes["match_len"] + 0.5]
print("Rows exceeding match length:", len(bad))   # must be 0

# --- Check 2: Khadija Shaw (exact name) -- expect 18 matches, ~1,510-1,530 real minutes ---
shaw = minutes[minutes["player"] == "Khadija Monifa Shaw"]
print("Shaw:", shaw["minutes"].sum(), "min across", len(shaw), "matches")

# --- Check 3: Global max should now be a plausible match length ---
print("Max single-match minutes:", minutes["minutes"].max())   # expect ~105-113

# --- Cleanup: drop the helper column before anyone reuses this table ---
minutes.drop(columns=["match_len"]).to_parquet(
    "assignment_5/models/player_match_minutes.parquet", index=False)