import pandas as pd
import streamlit as st


@st.cache_data
def calculate_rankings_for_all_seasons(df):
    """
    Calculate both Total Rank and Pos Rank for every season in the dataset.
    
    Args:
        df: DataFrame with player stats across multiple seasons
    
    Returns: DataFrame with Total Rank and Pos Rank added for each season
    """
    ranked_dfs = []
    
    for season in df['season'].unique():
        season_df = df[df['season'] == season].copy()
        
        # Calculate Total Rank (overall rank based on fantasy points per game)
        season_df['Total Rank'] = season_df['fantasy_points_per_game'].rank(
            ascending=False, 
            method='min'
        ).astype(int)
        
        # Calculate Pos Rank (positional rank within each position)
        season_df['Pos Rank'] = season_df.groupby('position')['fantasy_points_per_game'].rank(
            ascending=False, 
            method='min'
        ).astype(int)
        
        ranked_dfs.append(season_df)
    
    return pd.concat(ranked_dfs, ignore_index=True)


def get_current_season_rankings(df, season=2025):
    """
    Get player rankings filtered for a specific season with Total Rank and Pos Rank.
    """
    full_df = calculate_rankings_for_all_seasons(df)
    current_df = full_df[full_df['season'] == season].copy()
    current_df = current_df.sort_values('Total Rank')
    return current_df


def get_position_rankings(df, position, season=2025):
    """
    Get rankings filtered by position for a specific season.
    """
    season_df = get_current_season_rankings(df, season)
    position_df = season_df[season_df['position'] == position].copy()
    position_df = position_df.sort_values('Pos Rank')
    return position_df


def get_player_history_by_id(df, player_id):
    """
    Get all seasons of stats for a specific player by player_id with rankings.
    """
    full_df = calculate_rankings_for_all_seasons(df)
    player_df = full_df[full_df['player_id'] == player_id].copy()
    player_df = player_df.sort_values('season', ascending=False)
    return player_df


def get_main_table_columns():
    """Return the columns to display in the main 2025 rankings table."""
    return [
        'Total Rank',
        'Pos Rank',
        'player_display_name',
        'position',
        'recent_team',
        'fantasy_points_half_ppr',
        'games',
        'fantasy_points_per_game',
        'season_age',
        'years_exp',
        'apy',
        'contract_years_remaining'
    ]


def get_player_history_columns():
    """Return the columns to display in the player history table."""
    return [
        'season',
        'Total Rank',
        'Pos Rank',
        'player_display_name',
        'recent_team',
        'season_age',
        'fantasy_points_per_game',
        'games',
        'fantasy_points_half_ppr',
    ]


def get_position_specific_columns(position):
    """
    Return position-specific columns for detailed analysis.
    
    Args:
        position: 'QB', 'RB', 'WR', or 'TE'
    
    Returns: List of relevant columns for that position
    """
    base_cols = [
        'Pos Rank',
        'player_display_name',
        'recent_team',
        'season_age',
        'fantasy_points_per_game',
        'games'
    ]
    
    if position == 'QB':
        specific_cols = [
            'true_passing_talent',
            'dual_threat_score',
            'pressure_resilience',
            'passing_yards',
            'passing_tds',
            'passing_interceptions',
            'scramble_rush_share',
            'intended_air_yards_per_pass_attempt'
        ]
    elif position == 'RB':
        specific_cols = [
            'total_touch_share',
            'rb_complete_game',
            'receiving_back_score',
            'contact_balance',
            'rb_elusiveness_index',
            'workhorse_resilience',
            'rushing_yards',
            'receptions',
            'targets'
        ]
    elif position in ['WR', 'TE']:
        specific_cols = [
            'wopr',
            'target_value',
            'dominator_rating',
            'yptmpa',
            'separation_index',
            'yac_creator',
            'true_catch_rate',
            'air_yards_conversion',
            'targets',
            'receiving_yards'
        ]
    else:
        specific_cols = []
    
    return base_cols + specific_cols


def get_breakout_columns():
    """Return columns for breakout candidates table."""
    return [
        'player_display_name',
        'position',
        'recent_team',
        'season_age',
        'draft_round',
        'breakout_score',
        'norm_target_value',
        'norm_efficiency',
        'norm_target_share',
        'fantasy_points_per_game',
        'games'
    ]


def get_sell_high_columns():
    """Return columns for sell high candidates table."""
    return [
        'player_display_name',
        'position',
        'recent_team',
        'season_age',
        'sell_high_score',
        'norm_age_risk',
        'norm_target_share',
        'norm_efficiency',
        'norm_ypa_decline',
        'fantasy_points_per_game',
        'contract_years_remaining',
        'games'
    ]


def get_buy_low_columns():
    """Return columns for buy low candidates table."""
    return [
        'player_display_name',
        'position',
        'recent_team',
        'season_age',
        'buy_low_score',
        'air_yards_differential',
        'target_value',
        'youth_bonus',
        'fantasy_points_per_game',
        'games'
    ]


def format_dataframe_for_display(df, columns_list):
    """
    Format dataframe for display by renaming columns and selecting only specified columns.
    """
    display_df = df.copy()
    
    # Rename columns for better display
    column_renames = {
        'player_display_name': 'Player Name',
        'position': 'Position',
        'recent_team': 'Team',
        'season_age': 'Age',
        'years_exp': 'Years Exp',
        'games': 'Games',
        'fantasy_points_per_game': 'FP/G',
        'fantasy_points_half_ppr': 'Total FP',
        'season': 'Season',
        'apy': 'APY',
        'contract_years_remaining': 'Contract Yrs',
        'draft_round': 'Draft Rd',
        
        # QB metrics
        'true_passing_talent': 'Pass Talent',
        'dual_threat_score': 'Dual Threat',
        'pressure_resilience': 'Under Pressure',
        'scramble_rush_share': 'Scramble %',
        'intended_air_yards_per_pass_attempt': 'IAY/PA',
        'passing_yards': 'Pass Yds',
        'passing_tds': 'Pass TDs',
        'passing_interceptions': 'INTs',
        
        # RB metrics
        'total_touch_share': 'Touch Share',
        'rb_complete_game': 'Complete Game',
        'receiving_back_score': 'Receiving Score',
        'contact_balance': 'Contact Balance',
        'rb_elusiveness_index': 'Elusiveness',
        'workhorse_resilience': 'vs Loaded Box',
        'rushing_yards': 'Rush Yds',
        
        # WR/TE metrics
        'wopr': 'WOPR',
        'target_value': 'Target Value',
        'dominator_rating': 'Dominator',
        'yptmpa': 'YPTMPA',
        'separation_index': 'Separation',
        'yac_creator': 'YAC Creator',
        'true_catch_rate': 'True Catch %',
        'air_yards_conversion': 'Air Yds Conv',
        'targets': 'Targets',
        'receiving_yards': 'Rec Yds',
        'receptions': 'Rec',
        
        # Dynasty metrics
        'breakout_score': 'Breakout Score',
        'sell_high_score': 'Sell High Score',
        'buy_low_score': 'Buy Low Score',
        'draft_capital_score': 'Draft Capital',
        'air_yards_differential': 'Air Yds Diff',

        # Adds by LWD
        'norm_age_risk': 'Norm Age Risk',
        'norm_youth_bonus': 'Norm Youth Bonus',
        'norm_target_value': 'Norm Target Value',
        'norm_efficiency': 'Norm Efficiency',
        'norm_target_share': 'Norm Target Share',
        'norm_ypa_decline': 'Norm YPA Decline'
    }
    
    display_df = display_df.rename(columns=column_renames)
    
    # Update display_columns with renamed columns
    display_columns = [column_renames.get(col, col) for col in columns_list]
    
    # Only include columns that exist in the dataframe
    final_columns = [col for col in display_columns if col in display_df.columns]
    
    return display_df[final_columns]


def get_dynasty_candidates(df, candidate_type='breakout', min_games=8, top_n=30):
    """
    Get dynasty trade candidates based on type.
    
    Args:
        df: Enhanced DataFrame with composite metrics
        candidate_type: 'breakout', 'sell_high', or 'buy_low'
        min_games: Minimum games played to be considered
        top_n: Number of candidates to return
    
    Returns: Filtered and sorted DataFrame
    """
    # Filter for players with minimum games
    df_filtered = df[df['games'] >= min_games].copy()
    
    if candidate_type == 'breakout':
        # 2. Position Filter: Remove QBs from this specific view
        df_filtered = df_filtered[df_filtered['position'] != 'QB']
        # 3. Volume Floors: Statistical Significance Filters
        # WR/TE must have earned 25+ targets; RB must have 40+ carries
        volume_mask = (
            ((df_filtered['position'].isin(['WR', 'TE'])) & (df_filtered['targets'] >= 25)) | 
            ((df_filtered['position'] == 'RB') & (df_filtered['carries'] >= 40))
        )
        df_filtered = df_filtered[volume_mask]
        # 4. Age Filter
        df_filtered = df_filtered[df_filtered['season_age'] <= 25]
        sort_col = 'breakout_score'
        ascending = False
    elif candidate_type == 'sell_high':
        # 1. Aging Veteran Filter
        # RBs decline earlier (26+), WRs/TEs have a longer shelf life (28+)
        df_filtered = df_filtered[
            ((df_filtered['position'] == 'RB') & (df_filtered['season_age'] >= 26)) |
            ((df_filtered['position'].isin(['WR', 'TE'])) & (df_filtered['season_age'] >= 28))
        ]

        # 2. Volume Floor (Must be a "relevant" asset to be a 'Sell High')
        # We want players who are currently being treated as starters
        volume_mask = (
            ((df_filtered['position'].isin(['WR', 'TE'])) & (df_filtered['targets'] >= 60)) | 
            ((df_filtered['position'] == 'RB') & (df_filtered['carries'] >= 80))
        )
        df_filtered = df_filtered[volume_mask]

        # 3. Position Filter
        df_filtered = df_filtered[df_filtered['position'] != 'QB']

        sort_col = 'sell_high_score'
        ascending = False
    elif candidate_type == 'buy_low':
        # Players with unrealized production
        df_filtered = df_filtered[df_filtered['air_yards_differential'] > 0]
        sort_col = 'buy_low_score'
        ascending = False
    else:
        return pd.DataFrame()
    
    return df_filtered.sort_values(sort_col, ascending=ascending).head(top_n)


def render_internal_rankings_tab(all_data):
    """
    Render the Internal Player Rankings tab with enhanced dynasty metrics.
    
    Args:
        all_data: Enhanced DataFrame containing player statistics with composite metrics
    """
    st.title("Internal Player Rankings")
    
    try:
        # Validate that we have data
        if all_data is None or all_data.empty:
            st.error("No data available. Please check your data source.")
            return
        
        # Load current season rankings (2025)
        rankings_df = get_current_season_rankings(all_data, season=2025)
        
        if rankings_df.empty:
            st.warning("No data available for the 2025 season.")
            return
        
        # ===== MAIN RANKINGS TABLE =====
        st.header("📊 2025 Fantasy Rankings")
        
        # Get unique positions
        all_positions = ['All'] + sorted(rankings_df['position'].unique().tolist())
        
        # Position filter
        selected_position = st.selectbox(
            "Filter by Position:",
            all_positions,
            index=0,
            key="position_filter"
        )
        
        # Filter dataframe based on selection
        if selected_position == 'All':
            filtered_df = rankings_df.copy()
            filtered_df = filtered_df.sort_values('Total Rank')
        else:
            filtered_df = get_position_rankings(all_data, selected_position, season=2025)
        
        # Display stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Players", len(rankings_df))
        with col2:
            st.metric("Filtered Players", len(filtered_df))
        with col3:
            if selected_position != 'All':
                st.metric("Position", selected_position)
        
        # Get main table columns and format for display
        main_columns = get_main_table_columns()
        display_df = format_dataframe_for_display(filtered_df, main_columns)
        
        # Display the rankings table
        st.subheader(f"Overall Rankings - {selected_position}")
        
        # Create interactive dataframe with selection
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # ===== PLAYER HISTORY (when row selected) =====
        if event.selection and len(event.selection.rows) > 0:
            selected_row_index = event.selection.rows[0]
            selected_player = filtered_df.iloc[selected_row_index]
            
            st.divider()
            
            # Display player history
            st.subheader(f"📊 Career History: {selected_player['player_display_name']}")
            
            # Get player history using player_id
            player_history = get_player_history_by_id(
                all_data, 
                selected_player['player_id']
            )
            
            if not player_history.empty:
                # Show key career stats
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_seasons = len(player_history)
                    st.metric("Seasons Played", total_seasons)
                with col2:
                    total_games = player_history['games'].sum()
                    st.metric("Total Games", int(total_games))
                with col3:
                    avg_fpts = player_history['fantasy_points_half_ppr'].mean()
                    st.metric("Avg FP/Season", f"{avg_fpts:.1f}")
                with col4:
                    best_season = player_history['fantasy_points_half_ppr'].max()
                    st.metric("Best Season", f"{best_season:.1f}")
                
                # Display year-by-year stats
                st.subheader("Year-by-Year Statistics")
                
                history_columns = get_player_history_columns()
                history_display_df = format_dataframe_for_display(player_history, history_columns)
                
                st.dataframe(
                    history_display_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Show full detailed stats in expander
                with st.expander("View All Player Statistics"):
                    st.dataframe(
                        player_history,
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.info("No historical data available for this player.")
        
        st.divider()
        
        # ===== POSITION-SPECIFIC DEEP DIVES =====
        st.header("🎯 Position-Specific Analysis")
        st.write("Deep dive into position-specific metrics and advanced stats")
        
        for pos in ['QB', 'RB', 'WR', 'TE']:
            with st.expander(f"📈 {pos} Detailed Rankings"):
                pos_data = get_position_rankings(all_data, pos, season=2025)
                
                if not pos_data.empty:
                    # Get position-specific columns
                    pos_columns = get_position_specific_columns(pos)
                    pos_display = format_dataframe_for_display(pos_data, pos_columns)
                    
                    st.dataframe(
                        pos_display,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Add download button for this position
                    csv = pos_data.to_csv(index=False)
                    st.download_button(
                        label=f"Download {pos} Data",
                        data=csv,
                        file_name=f"{pos}_rankings_2025.csv",
                        mime="text/csv",
                        key=f"download_{pos}"
                    )
                else:
                    st.info(f"No data available for {pos}")
        
        st.divider()
        
        # ===== DYNASTY TRADE TARGETS =====
        st.header("💎 Dynasty Trade Targets")
        st.write("Identify players to target or sell based on advanced metrics")
        
        # Breakout Candidates
        with st.expander("🚀 Breakout Candidates (RB/WR/TE)"):
            st.write("Young players (≤25) with high breakout potential")
            
            breakout_df = get_dynasty_candidates(
                rankings_df, 
                candidate_type='breakout', 
                min_games=8, 
                top_n=30
            )
            
            if not breakout_df.empty:
                breakout_columns = get_breakout_columns()
                breakout_display = format_dataframe_for_display(breakout_df, breakout_columns)
                
                st.dataframe(
                    breakout_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                st.subheader("🚀 Breakout Methodology")

                st.caption("The **Breakout Score** identifies young talent positioned for a massive leap in production. It is calculated using a weighted composite of five key pillars:")

                st.markdown("""
                - **15% Pedigree (Draft Capital):** Higher draft picks receive more 'second chances' and a longer leash from coaching staffs.
                - **20% Timing (Youth Bonus):** Weights players in the 'breakout window' (Years 2-3), where physical development and playbook mastery peak.
                - **25% Value Efficiency (Norm Target Value):** Measures fantasy points per touch, normalized by position. High scores here indicate players who do more with every opportunity.
                - **25% Talent Grade (Norm Efficiency):** Uses 'Sticky' underlying stats (YPTMPA for WRs, Yards After Contact for RBs) to find players outperforming their peers regardless of volume.
                - **15% The Opportunity Gap (1 - Norm Target Share):** The 'Hidden Upside' factor. We reward players with high efficiency but lower current usage, as they are the prime candidates for a workload expansion.
                """)

                st.caption("⚠️ **Note**: Players who have already achieved a Top-12 positional finish receive a multiplier reduction to ensure the list highlights *emerging* talent rather than established superstars.")
            else:
                st.info("No breakout candidates found")
        
        # Sell High Candidates
        with st.expander("📉 Sell High Candidates (RB/WR/TE)"):
            st.write("Aging players with declining efficiency - sell before value drops")
            
            sell_high_df = get_dynasty_candidates(
                rankings_df, 
                candidate_type='sell_high', 
                min_games=8, 
                top_n=30
            )
            
            if not sell_high_df.empty:
                sell_columns = get_sell_high_columns()
                sell_display = format_dataframe_for_display(sell_high_df, sell_columns)
                
                st.dataframe(
                    sell_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                st.caption("⚖️ **Sell High Score**: Identifies high-value producers at significant risk of a value cliff. It balances current market perception against long-term sustainability using four pillars:")

                st.markdown("""
                - **20% The Age Cliff (Norm Age Risk):** Positional 'Apex' modeling that flags RBs past age 26 and WRs past 30. This captures the historical point where trade value begins to plummet regardless of production.
                - **25% Market Hype (Norm Target Share):** High usage actually *boosts* this score because you can only 'Sell High' on a player the market currently views as a high-volume starter.
                - **30% Efficiency Slide (Norm Efficiency):** Detects veterans who are surviving on volume but failing 'Under-the-Hood' (low YAC for RBs; low Separation for WRs).
                - **25% Regression Trigger (Norm YPA Decline):** Measures the drop-off in big-play ability by comparing current Yards Per Attempt/Target against career and positional averages.
                """)

                st.caption("📈 **Market Value Multiplier**: A dynamic adjustment that prioritizes players currently scoring in the Top 40% of their position. This ensures the list highlights active stars you can actually trade for a haul, rather than unproductive bench assets.")
            else:
                st.info("No sell high candidates found")
        
        # Buy Low Candidates
        with st.expander("💰 Buy Low Candidates (All Positions)"):
            st.write("Players with unrealized production - target in trades while undervalued")
            
            buy_low_df = get_dynasty_candidates(
                rankings_df, 
                candidate_type='buy_low', 
                min_games=8, 
                top_n=30
            )
            
            if not buy_low_df.empty:
                buy_columns = get_buy_low_columns()
                buy_display = format_dataframe_for_display(buy_low_df, buy_columns)
                
                st.dataframe(
                    buy_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                st.caption("🎯 **Buy Low Score**: High air yards differential and opportunity but low current production")
            else:
                st.info("No buy low candidates found")
        
        # Download button for current main view
        st.divider()
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label=f"Download {selected_position} Rankings as CSV",
            data=csv,
            file_name=f"{selected_position.lower()}_rankings_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    except Exception as e:
        st.error(f"Error loading rankings: {str(e)}")
        st.info("Please check your data format and ensure all required columns are present.")
        # Optionally show the full error for debugging
        with st.expander("Show full error details"):
            st.exception(e)