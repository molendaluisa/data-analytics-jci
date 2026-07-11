import os
import numpy as np
import pandas as pd

CACHE_EVENTS = "assignment_5/cache/events"

# --- Step 1: Load only Shot events, with the attributes worth slicing on ---
cols = ["match_id", "id", "player_id", "player", "team", "period",
        "minute", "second", "location", "play_pattern",
        "shot_outcome", "shot_type", "shot_body_part", "shot_technique",
        "shot_statsbomb_xg", "shot_first_time", "under_pressure"]
frames = []
for f in os.listdir(CACHE_EVENTS):
    df = pd.read_parquet(f"{CACHE_EVENTS}/{f}")
    keep = [c for c in cols if c in df.columns]
    frames.append(df[df["type"] == "Shot"][keep])
shots = pd.concat(frames, ignore_index=True)
print(f"Shots loaded: {len(shots):,}")

# --- Step 2: Unpack coordinates (same parquet-proof logic as 05) ---
def coord(v, i):
    if isinstance(v, (list, tuple, np.ndarray)) and len(v) > i:
        return float(v[i])
    return None

shots["x"] = shots["location"].apply(lambda v: coord(v, 0))
shots["y"] = shots["location"].apply(lambda v: coord(v, 1))
shots = shots.drop(columns=["location"])

# --- Step 3: Precompute geometry (goal centre is at x=120, y=40) ---
shots["distance"] = np.sqrt((120 - shots["x"])**2 + (40 - shots["y"])**2).round(1)
# Penalty box: x >= 102, 18 <= y <= 62
shots["inside_box"] = ((shots["x"] >= 102)
                       & (shots["y"].between(18, 62))).map({True: "Inside box",
                                                            False: "Outside box"})

# --- Step 4: Clean up types and labels for Power BI friendliness ---
shots["is_goal"] = (shots["shot_outcome"] == "Goal").astype(int)
shots["xg"] = shots["shot_statsbomb_xg"].fillna(0)
for flag in ["shot_first_time", "under_pressure"]:
    if flag in shots.columns:
        shots[flag] = shots[flag].fillna(False).astype(bool)

shots = shots.rename(columns={"shot_outcome": "outcome",
                              "shot_type": "shot_type",
                              "shot_body_part": "body_part",
                              "shot_technique": "technique",
                              "shot_first_time": "first_time"})
final_cols = ["match_id", "player_id", "player", "team", "period", "minute",
              "second", "x", "y", "distance", "inside_box", "play_pattern",
              "outcome", "is_goal", "shot_type", "body_part", "technique",
              "first_time", "under_pressure", "xg"]
shots = shots[[c for c in final_cols if c in shots.columns]]

# --- Step 5: Save (CSV for Power BI; parquet not needed for a table this small) ---
shots.to_csv("assignment_5/models/fact_shots.csv", index=False)
print(f"fact_shots: {len(shots):,} rows, {len(shots.columns)} columns")

# --- Check 1: Conservation -- goals here must equal the validated 420 ---
print("Goals in shots table:", shots["is_goal"].sum())        # expect 420

# --- Check 2: xG conservation vs. the fact table ---
fact = pd.read_parquet("assignment_5/models/fact_player_match.parquet")
print(f"xG here: {shots['xg'].sum():.2f} | xG in fact: {fact['xg'].sum():.2f}")  # must match

# --- Check 3: Slicing-column health -- no dominant nulls, sane categories ---
for c in ["play_pattern", "body_part", "inside_box", "outcome"]:
    print(f"\n{c}:")
    print(shots[c].value_counts(dropna=False).head(6))