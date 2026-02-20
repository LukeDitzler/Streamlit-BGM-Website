import nflreadpy as nfl
import pandas as pd
import streamlit as st
import requests

from sleeper_api import *
from roster_analysis import *
from nfl_info import *
from advanced_stats import *
from internal_rankings import *
from league_history import *

# Sleeper League ID's
LEAGUE_ID_2024 = "1099477523693473792"
LEAGUE_ID_2025 = "1182397104202231808"
LEAGUE_ID_2026 = "1314366510466076672"
# Sleeper Username
USERNAME = "LukeWickham"

# Page configuration
st.set_page_config(
    page_title="Big Green Machine HQ",
    page_icon="🏈",
    layout="wide"
)

# Create tabs
tabs = st.tabs(["Home", "Roster", "Trade Analyzer", "Internal Player Rankings", "History"])

# ===== HOME TAB =====
with tabs[0]:
    st.title("Big Green Machine HQ")
    st.write("NBTTM")

# ===== ROSTER TAB =====
with tabs[1]:
    st.title("BGM Roster & Playoff Analytics")

    # EXPANDER 1: CURRENT ROSTER
    with st.expander("📋 Current Roster", expanded=True):
        df = get_my_roster_dataframe(LEAGUE_ID_2026, USERNAME)
        # Defined static columns for a cleaner look
        display_cols = ['full_name', 'position', 'team', 'age', 'injury_status', 'years_exp']
        existing_cols = [c for c in display_cols if c in df.columns]
        
        st.dataframe(df[existing_cols], use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", data=csv, file_name="roster.csv", mime="text/csv")

    # EXPANDER 2: PLAYOFF PRODUCTION ANALYTICS
    with st.expander("📈 Performance vs Playoff Benchmarks", expanded=False):
        
        with st.spinner("Analyzing performance across all seasons..."):
            analysis_df = get_comprehensive_roster_analysis(
                LEAGUE_ID_2024, 
                LEAGUE_ID_2025, 
                LEAGUE_ID_2026, 
                USERNAME
            )
            
            if analysis_df is not None:
                    # Style the dataframe for better readability
                    def color_delta(val):
                        """Color negative deltas red, positive green"""
                        color = 'red' if val < 0 else 'green' if val > 0 else 'black'
                        return f'color: {color}'
                    
                    styled_df = analysis_df.style.format({
                        "2025 BGM Avg": "{:.2f}",
                        "2024 Playoff Avg": "{:.2f}",
                        "2025 Playoff Avg": "{:.2f}",
                        "Delta vs 2025 Playoff": "{:+.2f}"
                    }).applymap(color_delta, subset=['Delta vs 2025 Playoff'])
                    
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    # Summary Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        bgm_total = analysis_df["2025 BGM Avg"].sum()
                        st.metric("Your 2025 Avg Weekly Score", f"{bgm_total:.1f} pts")
                    
                    with col2:
                        playoff_2024_total = analysis_df["2024 Playoff Avg"].sum()
                        st.metric("2024 Playoff Avg", f"{playoff_2024_total:.1f} pts")

                    with col3:
                        playoff_2025_total = analysis_df["2025 Playoff Avg"].sum()
                        st.metric("2025 Playoff Avg", f"{playoff_2025_total:.1f} pts")
                    
                    with col4:
                        delta_total = analysis_df["Delta vs 2025 Playoff"].sum()
                        st.metric("Total Gap (2025)", f"{delta_total:+.1f} pts", 
                                 delta_color="inverse")

# ===== TRADE ANALYZER TAB =====
with tabs[2]:
    st.title("Trade Analyzer")
    st.info("Trade analysis features coming soon!")

# ===== INTERNAL PLAYER RANKINGS TAB =====
with tabs[3]:
    def load_all_data():
        # Construct dataset from nflreadpy
        adv_data = pd.read_csv('ff_player_basic_dataset.csv')
        # Add composit metrics
        full_data = add_trajectory_metrics(adv_data)
        adv_data = calculate_composite_metrics(full_data)
        # Return full set
        return adv_data

    # Load data
    all_data = load_all_data()

    render_internal_rankings_tab(all_data)

# ===== HISTORY TAB =====
league_ids = [LEAGUE_ID_2024, LEAGUE_ID_2025, LEAGUE_ID_2026]
bgm_history = get_franchise_history(league_ids, USERNAME)

with tabs[4]:
    st.title("History")
    
    # Get team/league stats for history
    league_info = get_league_info(LEAGUE_ID_2026)
    all_rosters = get_all_rosters(LEAGUE_ID_2026)
    league_users = get_league_users(LEAGUE_ID_2026)
    
    st.subheader("BGM Franchise History")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("All-Time Record", f"{bgm_history['total_wins']}-{bgm_history['total_losses']}-{bgm_history['total_ties']}")
    with col2: 
        st.metric("Seasons", bgm_history['seasons_played'])
    with col3:
        st.metric("Playoff Appearances", bgm_history['playoff_appearances'])
    with col4:
        st.metric("Championships", bgm_history['championships'])

    st.subheader(f"{league_info.get('name', 'League')} League History")
    
    # Get league-wide standings
    all_time_df = get_all_time_standings(league_ids)
    with st.expander("Total League History"):
        st.dataframe(all_time_df)
        
    # Individual seasons
    league_2024_df = get_season_by_season_records(LEAGUE_ID_2024)
    with st.expander("2024 League Results"):
        st.dataframe(league_2024_df, hide_index=True)

    league_2025_df = get_season_by_season_records(LEAGUE_ID_2025)
    with st.expander("2025 League Results"):
        st.dataframe(league_2025_df, hide_index=True)

    league_2026_df = get_season_by_season_records(LEAGUE_ID_2026)
    with st.expander("2026 League Results"):
        st.dataframe(league_2026_df, hide_index=True)
    
