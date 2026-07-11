import pandas as pd
from statsbombpy import sb

# --- Step 1: See all freely available competitions ---
comps = sb.competitions()
print(comps[["competition_id", "season_id", "competition_name", "season_name", "competition_gender"]].to_string())

# --- Step 2: Pull WSL 2023/24 matches ---
COMP_ID = 37      # FA Women's Super League
SEASON_ID = 281   # 2023/24 -- confirm against your comps output!

matches = sb.matches(competition_id=COMP_ID, season_id=SEASON_ID)

print(f"Matches found: {len(matches)}")
print(matches["match_date"].min(), matches["match_date"].max())
print(matches[["match_id", "match_date", "home_team", "away_team",
               "home_score", "away_score"]].head(10))


# --- Step 3: Save it -- this is pipeline input for the next step ---
matches.to_csv("assignment_5/models/matches_raw.csv", index=False)