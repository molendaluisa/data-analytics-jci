import os
import time
import pandas as pd
from statsbombpy import sb

# --- Step 1: Pulling events and lineups by looping over matches ---
CACHE_EVENTS = "assignment_5/cache/events"
CACHE_LINEUPS = "assignment_5/cache/lineups"

matches = pd.read_csv("assignment_5/models/matches_raw.csv")
match_ids = matches["match_id"].tolist()
print(f"Total matches to process: {len(match_ids)}")

failed = []

for i, mid in enumerate(match_ids, start=1):
    ev_path = f"{CACHE_EVENTS}/{mid}.parquet"
    lu_path = f"{CACHE_LINEUPS}/{mid}.parquet"

    try:
#         # --- Events ---
        events = sb.events(match_id=mid)
        events["match_id"] = mid
        events.to_parquet(ev_path, index=False)

        # --- Lineups (needed later for minutes played) ---
        lineups_dict = sb.lineups(match_id=mid)  # dict: team_name -> DataFrame
        lu_frames = []
        for team_name, df in lineups_dict.items():
            df = df.copy()
            df["team_name"] = team_name
            df["match_id"] = mid
            # positions/cards arrive as nested lists -> convert to JSON strings
            # (parquet can't store raw Python objects)
            for col in ["positions", "cards"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: pd.io.json.ujson_dumps(x)
                                            if isinstance(x, list) else x)
            lu_frames.append(df)
        pd.concat(lu_frames).to_parquet(lu_path, index=False)

        print(f"[{i}/{len(match_ids)}] cached match {mid}")
        time.sleep(0.5)  # be polite to the server

    except Exception as e:
        print(f"[{i}/{len(match_ids)}] FAILED match {mid}: {e}")
        failed.append(mid)

print(f"\nDone. Failed matches: {failed if failed else 'none'}")

# --- Step 2: Confirm all 132 matches are cached ---
print(len(os.listdir("assignment_5/cache/events")))   # confirmed 132
print(len(os.listdir("assignment_5/cache/lineups")))  # confirmed 132

# --- Step 3: Load one match and eyeball the event data ---
df = pd.read_parquet("assignment_5/cache/events/3912592.parquet")
print(len(df), "events")
print(df["type"].value_counts().head(10))