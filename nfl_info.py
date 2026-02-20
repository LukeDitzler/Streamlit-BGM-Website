import nflreadpy as nfl
import pandas as pd
import numpy as np

# --- 1. CORE DATA LOADERS ---

def get_player_stats(seasons=[2022, 2023, 2024, 2025]):
    """Loads and cleans base player seasonal stats with fantasy scoring."""
    base_cols = ["player_id", "player_display_name", "position", "season", "recent_team", "games"]
    
    POSITION_MAP = {
        'QB': base_cols + ["completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions", 
                           "sack_fumbles", "passing_epa", "carries", "rushing_yards", "rushing_tds", "fantasy_points"],
        'RB': base_cols + ["carries", "rushing_yards", "rushing_tds", "rushing_epa", "receptions", "targets", 
                           "receiving_yards", "receiving_tds", "fantasy_points"],
        'WR': base_cols + ["receptions", "targets", "receiving_yards", "receiving_tds", "receiving_air_yards", 
                           "receiving_epa", "target_share", "fantasy_points"],
        'TE': base_cols + ["receptions", "targets", "receiving_yards", "receiving_tds", "receiving_air_yards", 
                           "receiving_epa", "target_share", "fantasy_points"]
    }

    raw_stats = nfl.load_player_stats(seasons=seasons, summary_level='reg').to_pandas()
    
    position_dfs = []
    for pos, cols in POSITION_MAP.items():
        pos_df = raw_stats[raw_stats['position'] == pos].copy()
        existing_cols = [c for c in cols if c in pos_df.columns]
        position_dfs.append(pos_df[existing_cols])
    
    df = pd.concat(position_dfs, ignore_index=True)
    
    # Half-PPR Calculations
    df['receptions'] = df.get('receptions', 0).fillna(0)
    df['fantasy_points_half_ppr'] = df['fantasy_points'] + (0.5 * df['receptions'])
    df['fantasy_points_per_game'] = (df['fantasy_points_half_ppr'] / df['games']).replace([np.inf, -np.inf], 0).fillna(0)
    
    return df

def get_team_stats(seasons=[2022, 2023, 2024, 2025]):
    """Loads and cleans team seasonal totals to calculate market shares."""
    # We use 'team' here because that is the raw column name in team_stats
    base_cols = ["season", "team"]
    
    # Mirroring your stat categories (aggregated for the whole team)
    TEAM_METRICS = {
        'passing': ["attempts", "passing yards"],
        'rushing': ["carries", "rushing_yards", "rushing_tds"],
        'receiving': ["receptions", "receiving_yards", "receiving_tds"]
    }

    # Load raw team data (filtering for regular season)
    raw_teams = nfl.load_team_stats(seasons=seasons, summary_level='reg').to_pandas()
    
    # Flatten the METRICS dict into a single list of columns to keep
    all_metrics = [m for sublist in TEAM_METRICS.values() for m in sublist]
    existing_cols = [c for c in all_metrics if c in raw_teams.columns]
    
    # Filter and Copy
    df = raw_teams[base_cols + existing_cols].copy()

    # 1. Rename 'team' to 'recent_team' to align with player_stats for the merge
    df = df.rename(columns={'team': 'recent_team'})

    # 2. Add 'team_' prefix to all metric columns
    # We want to keep 'season' and 'recent_team' as join keys
    metric_rename = {col: f"team_{col}" for col in existing_cols}
    df = df.rename(columns=metric_rename)
    
    return df

def get_pfr_advstats_combined(seasons=[2022, 2023, 2024, 2025]):
    """Loads and merges PFR advanced passing, rushing, and receiving stats."""
    # Updated to match the exact column names from your environment
    stat_types = {
        'pass': ['pfr_id', 'season', 'team', 'drop_pct', 'bad_throw_pct', 'on_tgt_pct', 'pocket_time', 'pressure_pct', 'times_blitzed', 
                 'intended_air_yards_per_pass_attempt', 'completed_air_yards_per_pass_attempt', 'rpo_rush_att', 'rpo_rush_yards', 'scrambles', 'scramble_yards_per_attempt'],
        'rush': ['pfr_id', 'season', 'tm', 'ybc_att', 'yac_att', 'brk_tkl', 'att_br', 'x1d'],
        'rec': ['pfr_id', 'season', 'tm', 'adot', 'yac_r', 'ybc_r', 'brk_tkl', 'rec_br', 'x1d', 'drop_percent']
    }
    
    combined_pfr = None
    # Pre-load ID mapping to avoid repeated calls
    pfr_ids = nfl.load_players().to_pandas()[['gsis_id', 'pfr_id']].rename(columns={'gsis_id': 'player_id'})

    for s_type, requested_cols in stat_types.items():
        temp_df = nfl.load_pfr_advstats(seasons=seasons, stat_type=s_type, summary_level='season').to_pandas()
        
        if temp_df.empty:
            continue

        # 1. Standardize Team Column (Handle 'tm', 'Tm', 'team', 'Team')
        # We find any column that looks like 'team' or 'tm' and rename it to 'team'
        team_col = [c for c in temp_df.columns if c.lower() in ['team', 'tm']][0]
        temp_df = temp_df.rename(columns={team_col: 'team'})
        
        # 2. Ensure IDs and Season are columns (not indexes)
        temp_df = temp_df.reset_index() 
        
        # 3. Handle Midseason Trades (Total Rows)
        # Check if player has a 'TM' entry (e.g., '2TM', '3TM')
        temp_df['is_total_row'] = temp_df['team'].astype(str).str.contains('TM', na=False)
        has_total = temp_df.groupby(['pfr_id', 'season'])['is_total_row'].transform('any')
        temp_df = temp_df[(has_total & temp_df['is_total_row']) | (~has_total)].copy()

        # 4. Filter to columns that actually exist in this specific dataset
        # We always keep our merge keys: pfr_id, season, team
        actual_cols_to_keep = [c for c in requested_cols if c in temp_df.columns]
        temp_df = temp_df[actual_cols_to_keep]

        # 4b. Add Prefixes 
        if s_type in ['rush', 'rec']:
            # Rename columns except for our merge keys
            ignore_cols = ['pfr_id', 'season', 'team']
            temp_df = temp_df.rename(
                columns={c: f"{s_type}_{c}" for c in temp_df.columns if c not in ignore_cols}
            )

        # 5. Iterative Merge
        if combined_pfr is None:
            combined_pfr = temp_df
        else:
            # We merge on pfr_id and season. 
            # We don't merge on 'team' here because a player might have '2TM' 
            # in Passing but a specific team in Rushing if they only rushed for one team.
            combined_pfr = combined_pfr.merge(
                temp_df.drop(columns=['team'], errors='ignore'), 
                on=['pfr_id', 'season'], 
                how='outer'
            )

    if combined_pfr is not None:
        # Final join with GSIS IDs
        combined_pfr = combined_pfr.merge(pfr_ids, on='pfr_id', how='left')
        return combined_pfr.drop_duplicates(subset=['player_id', 'season'])
    
    return pd.DataFrame()

def get_ftn_stats(seasons=[2022, 2023, 2024, 2025]):
    """Aggregates FTN charting data to the player-season level."""
    ftn_play = nfl.load_ftn_charting(seasons=seasons).to_pandas()
    pbp_subset = nfl.load_pbp(seasons=seasons).to_pandas()[['game_id', 'play_id', 'receiver_player_id']]
    
    ftn_joined = ftn_play.merge(
        pbp_subset, 
        left_on=['nflverse_game_id', 'nflverse_play_id'], 
        right_on=['game_id', 'play_id'], 
        how='inner'
    )
    
    ftn_seasonal = ftn_joined.groupby(['receiver_player_id', 'season']).agg({
        'is_catchable_ball': 'sum',
        'is_contested_ball': 'sum',
        'is_drop': 'sum',
        'is_interception_worthy': 'sum'
    }).reset_index().rename(columns={'receiver_player_id': 'player_id'})
    
    return ftn_seasonal

# --- 2. EXISTING DATA LOADERS (Draft & Contracts) ---

def get_draft_data(positions=['QB', 'RB', 'WR', 'TE']):
    draft_picks = nfl.load_draft_picks(seasons=list(range(1995, 2026))).to_pandas()
    draft_df = draft_picks[draft_picks["position"].isin(positions)][
        ["gsis_id", "round", "pick", "team", "age"]
    ].rename(columns={"gsis_id": "player_id", "team": "draft_team", "round": "draft_round", "pick": "draft_pick_num", "age": "draft_age"})
    return draft_df

def get_contract_data(positions=['QB', 'RB', 'WR', 'TE']):
    contracts = nfl.load_contracts().to_pandas()
    contracts = contracts[contracts['position'].isin(positions)].dropna(subset=['years', 'year_signed'])
    contracts['otc_id'] = contracts['otc_id'].astype(str).str.strip()
    
    player_ids = nfl.load_players().to_pandas()[['gsis_id', 'otc_id']].rename(columns={'gsis_id': 'player_id'})
    player_ids['otc_id'] = player_ids['otc_id'].astype(str).str.strip()
    contracts = contracts.merge(player_ids, on='otc_id', how='inner')

    def expand_contract_years(row):
        try:
            start, total = int(float(row['year_signed'])), int(float(row['years']))
            return [{'player_id': row['player_id'], 'season': start + i, 'apy': row['apy'], 
                     'contract_years_remaining': (total - 1) - i, 'is_contract_year': 1 if (total - 1) - i == 0 else 0} 
                    for i in range(total)]
        except: return []

    all_rows = []
    for _, row in contracts.iterrows(): all_rows.extend(expand_contract_years(row))
    return pd.DataFrame(all_rows).drop_duplicates(subset=['player_id', 'season'], keep='last')

# --- 3. THE MASTER CONSTRUCTOR ---
def construct_intelligent_dataset(seasons=[2022, 2023, 2024, 2025], positions=['QB', 'RB', 'WR', 'TE']):
    """Orchestrates the modular functions into a single analytical dataset."""
    
    # 1. Fetch all components
    df_stats = get_player_stats(seasons)
    df_team = get_team_stats(seasons)
    df_pfr = get_pfr_advstats_combined(seasons)
    df_ftn = get_ftn_stats(seasons)
    df_draft = get_draft_data(positions)
    df_contracts = get_contract_data(positions)
    
    # 2. Roster Data for Birthdays/Exp
    rosters = nfl.load_rosters(seasons=seasons).to_pandas()
    roster_info = rosters[["gsis_id", "season", "birth_date", "years_exp"]].rename(columns={"gsis_id": "player_id"})

    # 3. Filter and Merge
    df = df_stats[df_stats['position'].isin(positions)].copy()
    
    # Join Team Stats
    df = df.merge(df_team, on=['recent_team', 'season'], how='left')
    
    # Join PFR Advanced Metrics
    df = df.merge(df_pfr, on=['player_id', 'season'], how='left')

    # Join FTN Charting
    df = df.merge(df_ftn, on=['player_id', 'season'], how='left')
    
    # Join Draft History
    df = df.merge(df_draft, on="player_id", how="left")
    
    # Join Roster Info
    df = df.merge(roster_info, on=["player_id", "season"], how="left")
    
    # Join Contract Status
    df = df.merge(df_contracts, on=["player_id", "season"], how="left")

    # 4. Final Calculations
    df['birth_date'] = pd.to_datetime(df['birth_date'], errors='coerce')
    df['season_age'] = df['season'] - df['birth_date'].dt.year
    df.loc[df['birth_date'].dt.month > 9, 'season_age'] -= 1

    final_df = df.sort_values(['player_id', 'season']).reset_index(drop=True)

    csv_dataset = final_df.to_csv("ff_player_basic_dataset.csv", index=False)
    return final_df