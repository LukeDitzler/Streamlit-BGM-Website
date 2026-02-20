import pandas as pd
import numpy as np


def add_trajectory_metrics(df):
    # Sort to ensure chronological order for shifting
    df = df.sort_values(['player_id', 'season'])
    
    # 1. Calculate Per-Touch Efficiency (Global)
    df['raw_per_touch_yards'] = np.where(
        df['position'] == 'RB',
        df['rushing_yards'] / df['carries'].replace(0, 1),
        df['receiving_yards'] / df['targets'].replace(0, 1)
    )
    
    # 2. Year-over-Year (YoY) Delta
    # We use groupby(player_id) so we don't accidentally compare one player's 2024 to a different player's 2023
    df['prev_efficiency'] = df.groupby('player_id')['raw_per_touch_yards'].shift(1)
    df['efficiency_delta'] = df['raw_per_touch_yards'] - df['prev_efficiency']
    
    # 3. Normalized Trajectory (Z-Score by Position)
    # This tells us: "Is this player's decline worse than the typical decline for their position?"
    df['norm_trajectory'] = df.groupby(['position', 'season'])['efficiency_delta'].transform(
        lambda x: (x - x.mean()) / (x.std() if x.std() != 0 else 1)
    )
    
    return df

def calculate_composite_metrics(df):
    """
    Calculate composite fantasy football metrics optimized for dynasty leagues.
    Focuses on efficiency, role security, and predictive indicators.
    
    Required team-level columns in dataset:
    - team_carries, team_rushing_yards, team_rushing_tds
    - team_receptions, team_receiving_yards, team_receiving_tds
    - team_attempts (team pass attempts)
    
    Parameters:
    -----------
    df : DataFrame
        Player stats with full schema including team aggregates
        
    Returns:
    --------
    DataFrame with additional composite metrics
    """
    df = df[df["games"] >= 8].copy()
    
    # ========== VERIFY REQUIRED COLUMNS EXIST ==========
    required_cols = [
        'team_carries', 'team_rushing_yards', 'team_rushing_tds',
        'team_receptions', 'team_receiving_yards', 'team_receiving_tds',
        'team_attempts'
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required team columns: {missing_cols}")
    
    # ========== UNIVERSAL METRICS ==========
    
    # Draft ROI - higher is better (later picks producing more)
    # Use log scale to prevent division issues with early picks
    df['draft_roi'] = np.where(
        df['draft_pick_num'].notna() & (df['draft_pick_num'] > 0),
        df['fantasy_points_per_game'] / np.log(df['draft_pick_num'] + 1),
        0
    )
    
    # Age-Adjusted Production (peak age curves differ by position)
    # RB peak: 24-26, WR/TE peak: 26-28
    def get_age_multiplier(row):
        if pd.isna(row['season_age']):
            return 1.0
        age = row['season_age']
        pos = row['position']
        
        if (pos == 'RB' and 24 <= age <= 26) or (pos in ['WR', 'TE'] and 26 <= age <= 28):
            return 1.2
        elif age <= 30:
            return 1.0
        else:
            return 0.85
    
    df['age_prime_multiplier'] = df.apply(get_age_multiplier, axis=1)
    df['age_adjusted_fpg'] = df['fantasy_points_per_game'] * df['age_prime_multiplier']
    
    # Contract Year Boost Indicator
    df['contract_year_boost'] = df['is_contract_year'].fillna(0).astype(int) * df['fantasy_points_per_game']
    
    # ========== QB METRICS ==========
    
    # Designed Rush Share (RPO tendency)
    df['designed_rush_share'] = np.where(
        df['carries'].fillna(0) > 0,
        df['rpo_rush_att'].fillna(0) / df['carries'],
        0
    )
    
    # Scramble Rush Share (improvisational ability)
    df['scramble_rush_share'] = np.where(
        df['carries'].fillna(0) > 0,
        df['scrambles'].fillna(0) / df['carries'],
        0
    )
    
    # Dual Threat Score (combines both rushing styles)
    df['dual_threat_score'] = (
        (df['designed_rush_share'] + df['scramble_rush_share']) * 
        df['scramble_yards_per_attempt'].fillna(0)
    )
    
    # Pressure Performance (EPA under pressure)
    df['pressure_resilience'] = np.where(
        df['pressure_pct'].fillna(0) > 0,
        df['passing_epa'].fillna(0) / (df['attempts'].fillna(1) * df['pressure_pct']),
        0
    )
    
    # True Passing Talent (combines accuracy, decision-making, depth)
    df['true_passing_talent'] = (
        df['on_tgt_pct'].fillna(0) * 0.4 +
        (1 - df['bad_throw_pct'].fillna(0)) * 0.3 +
        (1 - df['is_interception_worthy'].fillna(0).astype(float)) * 0.2 +
        df['intended_air_yards_per_pass_attempt'].fillna(0) / 10 * 0.1
    )
    
    # ========== RB METRICS ==========
    
    # Total Touch Share (using existing team columns)
    df['total_touch_share'] = np.where(
        (df['team_carries'] + df['team_receptions']) > 0,
        (df['carries'].fillna(0) + df['receptions'].fillna(0)) / 
        (df['team_carries'] + df['team_receptions']),
        0
    )
    
    # Contact Balance (prefer YAC > YBC = creates after contact)
    df['contact_balance'] = np.where(
        df['rush_ybc_att'].fillna(0) > 0,
        df['rush_yac_att'].fillna(0) / df['rush_ybc_att'],
        0
    )
    
    # Elusiveness Index
    df['rb_elusiveness_index'] = np.where(
        df['carries'].fillna(0) > 0,
        df['rush_brk_tkl'].fillna(0) / df['carries'],
        0
    )
    
    # Drive Dependency (first down creation)
    df['rb_drive_dependency'] = np.where(
        df['carries'].fillna(0) > 0,
        df['rush_x1d'].fillna(0) / df['carries'],
        0
    )
    
    # Receiving Back Score (PPR value indicator)
    df['receiving_back_score'] = (
        df['target_share'].fillna(0) * 2 +
        df['rec_yac_r'].fillna(0) / 10 +
        (df['receptions'].fillna(0) / df['games'].replace(0, 1))
    )

    # RB Complete Game Score
    df['rb_complete_game'] = (
        df['total_touch_share'] * 3 +
        df['rb_elusiveness_index'] * 10 +
        df['receiving_back_score'] * 0.5 +
        (df['rushing_tds'].fillna(0) + df['receiving_tds'].fillna(0)) / df['games'].replace(0, 1)
    )

    # WEIGHTED TOUCHES (RB-SPECIFIC) 
    # Targets worth ~2.8x carries in PPR leagues per AOD
    df['weighted_touches'] = (df['targets'].fillna(0) * 2.8) + df['carries'].fillna(0)
    
    # Workhorse Score (normalized weighted touches per game)
    df['workhorse_score'] = np.where(
        df['games'] > 0,
        df['weighted_touches'] / df['games'],
        0
    )
    
    # ========== WR/TE METRICS ==========
    
    # YPTMPA: Yards Per Team Pass Attempt
    df['yptmpa'] = np.where(
        df['team_attempts'].fillna(0) > 0,
        df['receiving_yards'].fillna(0) / df['team_attempts'],
        0
    )

    # Separation Index (measures how open they get)
    df['separation_index'] = np.where(
        df['rec_adot'].fillna(0) > 0,
        df['rec_ybc_r'].fillna(0) / df['rec_adot'],
        0
    )
    
    # YAC Creator (ability to generate after catch)
    df['yac_creator'] = np.where(
        (df['rec_ybc_r'].fillna(0) + df['rec_yac_r'].fillna(0)) > 0,
        df['rec_yac_r'].fillna(0) / 
        (df['rec_ybc_r'].fillna(0) + df['rec_yac_r'].fillna(0)),
        0
    )
    
    # Elusiveness Index
    df['wr_elusiveness_index'] = np.where(
        df['receptions'].fillna(0) > 0,
        df['rec_brk_tkl'].fillna(0) / df['receptions'],
        0
    )
    
    # Drive Dependency
    df['receiver_drive_dependency'] = np.where(
        df['receptions'].fillna(0) > 0,
        df['rec_x1d'].fillna(0) / df['receptions'],
        0
    )
    
    # Target Value (normalized for position to allow cross-positional ranking)
    df['target_value'] = np.where(
        df['position'] == 'RB',
        np.where(df['weighted_touches'] > 0, df['fantasy_points_half_ppr'] / df['weighted_touches'], 0),
        np.where(df['targets'] > 0, df['fantasy_points_half_ppr'] / df['targets'], 0)
    )
    
    # Creation Adjusted (age-weighted playmaking)
    df['receiver_creation_adj'] = np.where(
        df['season_age'].fillna(1) > 0,
        (df['rec_yac_r'].fillna(0) + df['rec_brk_tkl'].fillna(0) * 2) / df['season_age'],
        0
    )
    
    # True Catch Rate (adjusts for catchable balls if available)
    df['true_catch_rate'] = np.where(
        df['is_catchable_ball'].fillna(0) > 0,
        df['receptions'].fillna(0) / df['is_catchable_ball'],
        0
    )
    
    # Drop-Adjusted Target Value (accounts for player drops)
    df['drop_adjusted_target_value'] = df['target_value'] * (1 - df['rec_drop_percent'].fillna(0))
    
    # Contested Catch Ability (only if contested ball data exists)
    if 'is_contested_ball' in df.columns:
        df['contested_catch_rate'] = np.where(
            df['is_contested_ball'].fillna(0).astype(int) > 0,
            df['receptions'].fillna(0) / df['is_contested_ball'],
            0
        )
    else:
        df['contested_catch_rate'] = 0
    
    # Air Yards Conversion Rate
    df['air_yards_conversion'] = np.where(
        df['receiving_air_yards'].fillna(0) > 0,
        df['receiving_yards'].fillna(0) / df['receiving_air_yards'],
        0
    )
    
    # ========== AOD-INSPIRED COMPOSITE SCORES ==========
    
    # Air Yards Share (now using actual team_attempts!)
    df['air_yards_share'] = np.where(
        df['team_attempts'] > 0,
        df['receiving_air_yards'].fillna(0) / df['team_attempts'],
        0
    )
    
    # WOPR (Weighted Opportunity Rating) - AOD's best predictor
    # Formula: 1.5 * Target Share + 0.7 * Air Yards Share
    df['wopr'] = (1.5 * df['target_share'].fillna(0)) + (0.7 * df['air_yards_share'])
    
    # Dominator Rating (using existing team columns)
    df['rec_yards_share'] = np.where(
        df['team_receiving_yards'] > 0,
        df['receiving_yards'].fillna(0) / df['team_receiving_yards'],
        0
    )
    df['rec_td_share'] = np.where(
        df['team_receiving_tds'] > 0,
        df['receiving_tds'].fillna(0) / df['team_receiving_tds'],
        0
    )
    df['dominator_rating'] = (df['rec_yards_share'] + df['rec_td_share']) / 2
    
    # YPTMPA (Yards Per Team Pass Attempt) - "sticky" metric
    # This is the AOD efficiency metric for finding value in low-volume offenses
    df['yptmpa'] = np.where(
        df['team_attempts'] > 0,
        df['receiving_yards'].fillna(0) / df['team_attempts'],
        0
    )

    # ========== DYNASTY-SPECIFIC INDICATORS ==========
    
    # Draft Capital Score
    df['draft_capital_score'] = np.where(
        df['draft_round'].notna(),
        (8 - df['draft_round'].clip(1, 7)),
        0
    )

    # 1. Calculate raw "Years Past Apex"
    # Apex: RB=24.5, WR/TE=26.5
    df['years_past_apex'] = np.where(
        df['position'] == 'RB',
        (df['season_age'] - 24.5).clip(0),
        (df['season_age'] - 26.5).clip(0)
    )

    # 2. Normalize it (Z-Score)
    df['norm_age_risk'] = df.groupby('position')['years_past_apex'].transform(
        lambda x: (x - x.mean()) / (x.std() if x.std() != 0 else 1)
    )

    # Norm Youth Bonus (Inverse of Age Risk)
    df['norm_youth_bonus'] = df['norm_age_risk'] * -1

    # --- BREAKOUT ---
    # 1. Define the "Arrival" line (Top 25% of each position)
    # Anyone above this line is considered "Already a Star"
    df['arrival_threshold'] = df.groupby('position')['fantasy_points_per_game'].transform(
        lambda x: x.quantile(0.75)
    )

    # 2. Create the Multiplier
    # Players who HAVEN'T hit the threshold get a "Potential Boost" (1.2x)
    # Players who HAVE hit it get an "Established Penalty" (0.7x)
    df['breakout_multiplier'] = np.where(
        df['fantasy_points_per_game'] < df['arrival_threshold'], 
        1.2, 
        0.7
    )

    # 2. Standardize target_value by position (Z-Score)
    # This fixes the "RB target_value is too small" problem by centering everyone at 0
    df['norm_target_value'] = df.groupby('position')['target_value'].transform(
        lambda x: (x - x.mean()) / (x.std() if x.std() != 0 else 1)
    )

    df['norm_target_share'] = df.groupby('position')['target_share'].transform(
        lambda x: (x - x.mean()) / (x.std() if x.std() != 0 else 1)
    )

    # 1. Define Position-Specific "Under-the-Hood" Efficiency
    # For RBs: Yards After Contact per Attempt (rush_yac_att)
    # For WRs: YPTMPA (The YPRR Proxy)
    df['raw_efficiency'] = np.where(
        df['position'] == 'RB',
        df['rush_yac_att'].fillna(0),
        df['yptmpa'].fillna(0)
    )

    # 2. Normalize by position so RBs and WRs can coexist on the same list
    df['norm_efficiency'] = df.groupby('position')['raw_efficiency'].transform(
        lambda x: (x - x.mean()) / (x.std() if x.std() != 0 else 1)
    )

    # 3. Apply it to your final score
    df['breakout_score'] = (
        df['draft_capital_score'] * 0.15 +      
        df['norm_youth_bonus'] * 0.20 +              
        df['norm_target_value'] * 0.25 +        
        df['norm_efficiency'] * 0.25 +          
        (1 - df['norm_target_share'].fillna(0)) * 0.15 
    ) * df['breakout_multiplier']

    # Apply a smoother "Arrival Penalty"
    # Instead of a hard cut, we use a multiplier for players who haven't "arrived" yet
    df['arrival_multiplier'] = np.where(df['fantasy_points_per_game'] < df['arrival_threshold'], 1.2, 0.7)
    df['breakout_score'] *= df['arrival_multiplier']
    

    # --- SELL HIGH ---
    # 1. Define "Current Value" threshold (Top 40% of scorers at position)
    df['value_threshold'] = df.groupby('position')['fantasy_points_per_game'].transform(
        lambda x: x.quantile(0.60)
    )

    # 2. Create the Multiplier
    # Players producing ABOVE the threshold are the only ones you can "Sell High"
    # If they aren't producing, they are just "Roster Clogs" (Penalty)
    df['market_value_multiplier'] = np.where(
        df['fantasy_points_per_game'] >= df['value_threshold'], 
        1.3, # Boost the actual producers
        0.5  # Penalize the "already dead" assets
    )

    # 1. Calculate Raw Per-Touch Efficiency
    # We use np.where to handle the positional split
    df['raw_per_touch_yards'] = np.where(
        df['position'] == 'RB',
        df['rushing_yards'] / df['carries'].replace(0, 1), # Avoid division by zero
        df['receiving_yards'] / df['targets'].replace(0, 1)
    )

    # 2. Normalize by Position (The 'Decline' Factor)
    # We calculate the Z-Score, then multiply by -1 
    # Because a LOWER yardage score should result in a HIGHER 'Decline Risk'
    df['norm_ypa_decline'] = df.groupby('position')['raw_per_touch_yards'].transform(
        lambda x: (x.mean() - x) / (x.std() if x.std() != 0 else 1)
    )

    # Sell High: High Volume + High Age + Dropping Efficiency
    df['sell_high_score'] = (
        df['norm_age_risk'] * 0.20 +          # Weight 1: Aging assets (The 'Cliff')
        df['norm_target_share'] * 0.25 +     # Weight 2: High volume (The 'Hype')
        df['norm_efficiency'] * -0.30 + # Weight 3: Bad 'Under-the-Hood' stats
        df['norm_trajectory'] * -0.25       # Weight 4: Declining per-touch stats
    ) * df['market_value_multiplier']

    # --- BUY LOW ---   
    # Air Yards Differential (unrealized production)
    df['air_yards_differential'] = (
        df['receiving_air_yards'].fillna(0) - 
        df['receiving_yards'].fillna(0)
    )
    
    # Buy Low Score (unrealized production + youth + opportunity)
    df['buy_low_score'] = (
        (df['air_yards_differential'] / 100).clip(0, 5) * 0.30 +
        df['norm_youth_bonus'] * 0.20 +
        df['target_share'].fillna(0) * 10 * 0.25 +
        df['draft_capital_score'] * 0.15 +
        (1 / (df['fantasy_points_per_game'] + 0.1)).clip(0, 2) * 0.10
    )
    
    # Consistency Score (approximate - higher is more consistent)
    df['consistency_score'] = np.where(
        df['games'] > 8,
        df['fantasy_points_per_game'] / (df['games'].replace(0, 1)),
        0
    )
    
    return df


def generate_dynasty_rankings(df, position='WR', sort_by='breakout_score', top_n=50):
    """
    Generate dynasty-optimized rankings.
    
    Parameters:
    -----------
    df : DataFrame
        DataFrame with composite metrics
    position : str
        'WR', 'RB', 'TE', or 'QB'
    sort_by : str
        Metric to sort by (default: 'breakout_score')
    top_n : int
        Number of players to return
        
    Returns:
    --------
    Ranked DataFrame
    """
    pos_df = df[df['position'] == position].copy()
    
    # Position-specific key metrics
    if position == 'QB':
        key_metrics = ['fantasy_points_per_game', 'true_passing_talent', 
                      'dual_threat_score', 'pressure_resilience', 'season_age']
    elif position == 'RB':
        key_metrics = ['fantasy_points_per_game', 'total_touch_share', 
                      'rb_complete_game', 'receiving_back_score', 'target_value',
                      'contact_balance', 'workhorse_score', 'season_age']
    elif position in ['WR', 'TE']:
        key_metrics = ['fantasy_points_per_game', 'wopr', 'target_value',
                      'dominator_rating', 'yptmpa', 'separation_index',
                      'yac_creator', 'breakout_score', 'season_age']
    else:
        return pd.DataFrame()
    
    display_cols = ['player_display_name', 'recent_team', 'season', 
                   'games', 'draft_round'] + key_metrics
    
    # Filter to only columns that exist
    display_cols = [col for col in display_cols if col in pos_df.columns]
    
    ranked = pos_df[display_cols].sort_values(sort_by, ascending=False).head(top_n)
    ranked.insert(0, 'rank', range(1, len(ranked) + 1))
    
    return ranked
