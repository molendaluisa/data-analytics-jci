import os
import numpy as np
import pandas as pd

CACHE_EVENTS = "assignment_5/cache/events"

# --- Step 1: Load all events, keeping only the columns we aggregate on ---
cols = ["match_id", "type", "player_id", "player", "team",
        "location", "pass_end_location", "carry_end_location",
        "pass_outcome", "pass_shot_assist", "pass_goal_assist",
        "shot_outcome", "shot_type", "shot_statsbomb_xg",
        "dribble_outcome", "duel_type"]
frames = []
for f in os.listdir(CACHE_EVENTS):
    df = pd.read_parquet(f"{CACHE_EVENTS}/{f}")
    keep = [c for c in cols if c in df.columns]   # some columns absent in some matches
    frames.append(df[keep])
ev = pd.concat(frames, ignore_index=True)
print(f"Events loaded: {len(ev):,}")

# --- Step 2: Derive helper columns ---
# Coordinate extraction that survives the parquet round-trip:
# lists may come back as numpy arrays, so handle list, tuple, AND ndarray.
def first_coord(v):
    """Return x from a location stored as list, tuple, or numpy array; else None."""
    if isinstance(v, (list, tuple, np.ndarray)) and len(v) >= 1:
        return float(v[0])
    return None

# x-coordinates of action start/end (StatsBomb: x runs 0 -> 120 toward opponent goal)
ev["x_start"] = ev["location"].apply(first_coord)
ev["x_pass_end"] = ev["pass_end_location"].apply(first_coord)
ev["x_carry_end"] = ev["carry_end_location"].apply(first_coord)

is_pass = ev["type"] == "Pass"
is_carry = ev["type"] == "Carry"
is_shot = ev["type"] == "Shot"

# Goals, shots, xG (np_ = non-penalty, the fairer basis for finishing analysis)
ev["goal"] = (is_shot & (ev["shot_outcome"] == "Goal")).astype(int)
ev["shot"] = is_shot.astype(int)
ev["penalty"] = (is_shot & (ev["shot_type"] == "Penalty")).astype(int)
ev["xg"] = ev["shot_statsbomb_xg"].fillna(0)
ev["np_xg"] = ev["xg"].where(ev["penalty"] == 0, 0)
ev["np_goal"] = ev["goal"].where(ev["penalty"] == 0, 0)

# Pass bookkeeping: in StatsBomb data, pass_outcome is NaN for COMPLETED passes
ev["pass_att"] = is_pass.astype(int)
ev["pass_cmp"] = (is_pass & (ev["pass_outcome"].isna())).astype(int)
ev["assist"] = ev["pass_goal_assist"].fillna(False).astype(bool).astype(int)
ev["key_pass"] = ev["pass_shot_assist"].fillna(False).astype(bool).astype(int)

# Progressive actions: completed, moving the ball >= 15 units toward goal
PROG = 15
ev["prog_pass"] = (is_pass & ev["pass_outcome"].isna()
                   & ((ev["x_pass_end"] - ev["x_start"]) >= PROG)).astype(int)
ev["prog_carry"] = (is_carry
                    & ((ev["x_carry_end"] - ev["x_start"]) >= PROG)).astype(int)

# Defensive & dribbling counts
ev["dribble_cmp"] = ((ev["type"] == "Dribble") & (ev["dribble_outcome"] == "Complete")).astype(int)
ev["pressure"] = (ev["type"] == "Pressure").astype(int)
ev["tackle"] = ((ev["type"] == "Duel") & (ev["duel_type"] == "Tackle")).astype(int)
ev["interception"] = (ev["type"] == "Interception").astype(int)
ev["recovery"] = (ev["type"] == "Ball Recovery").astype(int)

# --- Step 3: Aggregate to one row per player per match ---
agg_cols = ["goal", "np_goal", "shot", "penalty", "xg", "np_xg",
            "pass_att", "pass_cmp", "assist", "key_pass",
            "prog_pass", "prog_carry", "dribble_cmp",
            "pressure", "tackle", "interception", "recovery"]
fact = (ev.dropna(subset=["player_id"])
          .groupby(["match_id", "player_id", "player", "team"], as_index=False)[agg_cols]
          .sum())

# --- Step 4: Join minutes played (inner join -- both sides must agree) ---
minutes = pd.read_parquet("assignment_5/models/player_match_minutes.parquet")
fact = fact.merge(minutes[["match_id", "player_id", "minutes"]],
                  on=["match_id", "player_id"], how="inner")

# --- Step 5: Save the fact table (parquet for us, CSV for Power BI) ---
fact.to_parquet("assignment_5/models/fact_player_match.parquet", index=False)
fact.to_csv("assignment_5/models/fact_player_match.csv", index=False)
print(f"Fact table rows: {len(fact):,}")

# --- Check 1: Conservation -- fact-table goals must equal the validated 420 ---
print("Total goals:", fact["goal"].sum())          # confirmed 420

# --- Check 2: Join integrity -- how many event-players lacked minutes rows? ---
n_event_players = ev.dropna(subset=["player_id"]).groupby(["match_id", "player_id"]).ngroups
print("Player-match combos in events:", n_event_players, "| in fact after join:", len(fact))

# --- Check 3: Smell test -- top 5 by np_xG and by progressive carries ---
season = fact.groupby("player")[["xg", "np_xg", "goal", "prog_carry", "prog_pass"]].sum()
print("\n--- Top 5 by np_xG ---")
print(season.sort_values("np_xg", ascending=False).head(5).to_string())
print("\n--- Top 5 by progressive carries ---")
print(season.sort_values("prog_carry", ascending=False).head(5).to_string())