import os
import json
import pandas as pd

CACHE_LINEUPS = "assignment_5/cache/lineups"

# --- Step 1: dim_match -- straight from the matches file we already validated ---
matches = pd.read_csv("assignment_5/models/matches_raw.csv")
dim_match = matches[["match_id", "match_date", "match_week",
                     "home_team", "away_team", "home_score", "away_score"]].copy()
dim_match["match_date"] = pd.to_datetime(dim_match["match_date"])
dim_match.to_csv("assignment_5/models/dim_match.csv", index=False)
print(f"dim_match: {len(dim_match)} rows")

# --- Step 2: dim_team -- distinct teams (12 expected) ---
dim_team = (pd.concat([matches["home_team"], matches["away_team"]])
              .drop_duplicates().sort_values()
              .reset_index(drop=True).to_frame("team_name"))
dim_team["team_id"] = dim_team.index + 1
dim_team.to_csv("assignment_5/models/dim_team.csv", index=False)
print(f"dim_team: {len(dim_team)} rows")   # expect 12

# --- Step 3: dim_player -- one row per player, with primary position ---
# 3a: collect every positional stint from every lineup file
stints = []
for f in os.listdir(CACHE_LINEUPS):
    lu = pd.read_parquet(f"{CACHE_LINEUPS}/{f}")
    for _, r in lu.iterrows():
        positions = json.loads(r["positions"]) if isinstance(r["positions"], str) else []
        for st in positions:
            stints.append({"player_id": r["player_id"],
                           "player": r["player_name"],
                           "team": r["team_name"],
                           "position": st["position"]})
stints = pd.DataFrame(stints)

# 3b: primary position = the position a player was fielded in most often
primary_pos = (stints.groupby(["player_id", "player", "position"]).size()
                     .reset_index(name="n")
                     .sort_values("n", ascending=False)
                     .drop_duplicates("player_id"))

# 3c: primary team = the team she appeared for most (guards against any mid-season moves)
primary_team = (stints.groupby(["player_id", "team"]).size()
                      .reset_index(name="n")
                      .sort_values("n", ascending=False)
                      .drop_duplicates("player_id"))

dim_player = primary_pos[["player_id", "player", "position"]].merge(
    primary_team[["player_id", "team"]], on="player_id")

# 3d: coarse position group for practical slicing
def pos_group(p):
    if "Goalkeeper" in p:
        return "Goalkeeper"
    if "Back" in p:                      # Center Back, Left Back, Right Wing Back...
        return "Defender"
    if "Midfield" in p:                  # Defensive/Center/Attacking Midfield etc.
        return "Midfielder"
    return "Forward"                     # Center Forward, Wings, Second Striker

dim_player["position_group"] = dim_player["position"].apply(pos_group)
dim_player.to_csv("assignment_5/models/dim_player.csv", index=False)
print(f"dim_player: {len(dim_player)} rows")

# --- Step 4: dim_date -- one row per calendar day across the season ---
dates = pd.date_range(dim_match["match_date"].min(),
                      dim_match["match_date"].max(), freq="D")
dim_date = pd.DataFrame({"date": dates})
dim_date["year"] = dim_date["date"].dt.year
dim_date["month"] = dim_date["date"].dt.month
dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
dim_date["week"] = dim_date["date"].dt.isocalendar().week.astype(int)
dim_date["day_name"] = dim_date["date"].dt.strftime("%a")
dim_date.to_csv("assignment_5/models/dim_date.csv", index=False)
print(f"dim_date: {len(dim_date)} rows")

# --- Check 1: Referential integrity -- every fact row must find its dimensions ---
fact = pd.read_parquet("assignment_5/models/fact_player_match.parquet")
orphan_players = set(fact["player_id"]) - set(dim_player["player_id"])
orphan_matches = set(fact["match_id"]) - set(dim_match["match_id"])
print("Orphan player_ids in fact:", len(orphan_players))   # must be 0
print("Orphan match_ids in fact:", len(orphan_matches))    # must be 0

# --- Check 2: Position group distribution -- should look like football ---
print(dim_player["position_group"].value_counts())

# --- Check 3: Spot-check three players whose real positions you know ---
for name in ["Khadija Monifa Shaw", "Alex Greenwood", "Lauren Hemp"]:
    row = dim_player[dim_player["player"] == name]
    print(row[["player", "position", "position_group", "team"]].to_string(index=False))