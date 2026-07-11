import os
import pandas as pd

CACHE_EVENTS = "assignment_5/cache/events"

# --- Step 1: Load ALL cached event files into one DataFrame ---
# (only the columns we need, to keep memory light)
cols = ["match_id", "type", "player", "team", "shot_outcome", "shot_type", "period"]
frames = []
for f in os.listdir(CACHE_EVENTS):
    df = pd.read_parquet(f"{CACHE_EVENTS}/{f}", columns=cols)
    frames.append(df)
events = pd.concat(frames, ignore_index=True)
print(f"Total events loaded: {len(events):,}")

# --- Step 2: Filter to goals ---
# A goal = an event of type "Shot" whose shot_outcome is "Goal".
# Note: own goals are logged as a separate event type ("Own Goal Against"),
# NOT as shots -- so they are correctly excluded from a scorer ranking.
goals = events[(events["type"] == "Shot") & (events["shot_outcome"] == "Goal")]
print(f"Total goals in the season: {len(goals)}")

# --- Step 3: Build the top-scorer table ---
top_scorers = (goals.groupby(["player", "team"])
                    .size()
                    .sort_values(ascending=False)
                    .head(10))
print("\n--- Top 10 scorers, WSL 2023/24 (from our pipeline) ---")
print(top_scorers.to_string())

# --- Step 4: Hard assertion -- fail loudly if reality disagrees ---
top_player = top_scorers.index[0][0]
top_goals = top_scorers.iloc[0]
assert "Shaw" in top_player and top_goals == 21, (
    f"VALIDATION FAILED: expected Khadija Shaw with 21, got {top_player} with {top_goals}"
)
print("\n✅ Validation passed: Khadija Shaw, 21 goals -- matches the official Golden Boot.")