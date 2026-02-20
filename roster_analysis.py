import requests
import streamlit as st
import pandas as pd
import numpy as np

BASE_URL = "https://api.sleeper.app/v1"

def get_playoff_roster_ids(league_id):
    bracket = requests.get(f"{BASE_URL}/league/{league_id}/winners_bracket").json()
    # Pulls team IDs that participated in the semi-finals/finals
    playoff_teams = {match[t] for match in bracket for t in ['t1', 't2'] if match.get(t)}
    return list(playoff_teams)

def get_user_roster_id(league_id, username):
    """Get the roster_id for a specific username"""
    users = requests.get(f"{BASE_URL}/league/{league_id}/users").json()
    rosters = requests.get(f"{BASE_URL}/league/{league_id}/rosters").json()
    
    # Find user_id from username
    user_id = None
    for user in users:
        if user['display_name'] == username or user.get('username') == username:
            user_id = user['user_id']
            break
    
    if not user_id:
        return None
    
    # Find roster_id from user_id
    for roster in rosters:
        if roster['owner_id'] == user_id:
            return roster['roster_id']
    
    return None

def label_roster_slots(starter_data):
    """
    Sorts players into specific slots: QB1, RB1, RB2, WR1, WR2, WR3, TE1, 
    Flex1, Flex2, Superflex1 based on weekly production.
    """
    # Sort all starters by points descending
    starters = sorted(starter_data, key=lambda x: x['pts'], reverse=True)
    
    slots = {}
    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'FLEX': 0, 'SF': 0}
    
    # 1. Fill Primary Slots first
    remaining = []
    for s in starters:
        pos = s['pos']
        if pos == 'QB' and counts['QB'] < 1:
            slots['QB1'] = s['pts']; counts['QB'] += 1
        elif pos == 'RB' and counts['RB'] < 2:
            counts['RB'] += 1; slots[f'RB{counts["RB"]}'] = s['pts']
        elif pos == 'WR' and counts['WR'] < 3:
            counts['WR'] += 1; slots[f'WR{counts["WR"]}'] = s['pts']
        elif pos == 'TE' and counts['TE'] < 1:
            slots['TE1'] = s['pts']; counts['TE'] += 1
        else:
            remaining.append(s)

    # 2. Fill Flex (RB/WR/TE)
    final_remain = []
    for s in remaining:
        if s['pos'] in ['RB', 'WR', 'TE'] and counts['FLEX'] < 2:
            counts['FLEX'] += 1; slots[f'Flex{counts["FLEX"]}'] = s['pts']
        else:
            final_remain.append(s)
            
    # 3. Fill Superflex (Any)
    if final_remain:
        slots['Superflex1'] = final_remain[0]['pts']
        
    return slots

def fetch_season_positional_avg(league_id, roster_ids=None):
    """
    Calculate positional averages for specified roster_ids.
    If roster_ids is None, calculates for playoff teams.
    """
    if roster_ids is None:
        roster_ids = get_playoff_roster_ids(league_id)
    elif not isinstance(roster_ids, list):
        roster_ids = [roster_ids]
    
    players = requests.get(f"{BASE_URL}/players/nfl").json()
    
    weekly_results = []
    for week in range(1, 15):
        matchups = requests.get(f"{BASE_URL}/league/{league_id}/matchups/{week}").json()
        for team in matchups:
            if team['roster_id'] in roster_ids:
                starter_data = [
                    {'pos': players.get(p_id, {}).get('position'), 'pts': team['starters_points'][i]}
                    for i, p_id in enumerate(team['starters']) if p_id != "0"
                ]
                weekly_results.append(label_roster_slots(starter_data))
                
    return pd.DataFrame(weekly_results).mean().to_dict()

def get_comprehensive_roster_analysis(league_id_2024, league_id_2025, league_id_2026, username):
    """
    Creates a comprehensive analysis comparing:
    - User's 2025 performance
    - 2024 playoff team averages
    - 2025 playoff team averages
    """
    # Get user's roster_id for 2025
    user_roster_id = get_user_roster_id(league_id_2025, username)
    
    if not user_roster_id:
        st.error(f"Could not find roster for username: {username}")
        return None
    
    # Calculate all averages
    bgm_2025_avg = fetch_season_positional_avg(league_id_2025, user_roster_id)
    playoff_2024_avg = fetch_season_positional_avg(league_id_2024)
    playoff_2025_avg = fetch_season_positional_avg(league_id_2025)
    
    # Define position order
    position_order = ['QB1', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE1', 'Flex1', 'Flex2', 'Superflex1']
    
    # Build DataFrame
    df = pd.DataFrame({
        "Position Slot": position_order,
        "2025 BGM Avg": [bgm_2025_avg.get(pos, 0) for pos in position_order],
        "2024 Playoff Avg": [playoff_2024_avg.get(pos, 0) for pos in position_order],
        "2025 Playoff Avg": [playoff_2025_avg.get(pos, 0) for pos in position_order]
    })
    
    # Calculate delta (negative = underproducing)
    df["Delta vs 2025 Playoff"] = df["2025 BGM Avg"] - df["2025 Playoff Avg"]
    
    return df

def render_roster_tab(league_id_2024, league_id_2025):
    st.header("Playoff Production Analysis")
    st.write("Average weekly points generated by Playoff Teams per starting slot.")

    if st.button("Run Analytics"):
        with st.spinner("Crunching Sleeper Data..."):
            # Fetch data for both seasons
            data_2024 = fetch_season_positional_avg(league_id_2024)
            data_2025 = fetch_season_positional_avg(league_id_2025)

            # Combine into a clean DataFrame
            all_pos = sorted(list(set(data_2024.keys()) | set(data_2025.keys())))
            
            comparison_df = pd.DataFrame({
                "Position Slot": all_pos,
                "2024 Avg Pts": [data_2024.get(p, 0) for p in all_pos],
                "2025 Avg Pts": [data_2025.get(p, 0) for p in all_pos]
            })

            # Formatting
            comparison_df["2024 Avg Pts"] = comparison_df["2024 Avg Pts"].map("{:.2f}".format)
            comparison_df["2025 Avg Pts"] = comparison_df["2025 Avg Pts"].map("{:.2f}".format)

            st.table(comparison_df)
            
            # Insights
            total_24 = pd.to_numeric(comparison_df["2024 Avg Pts"]).sum()
            total_25 = pd.to_numeric(comparison_df["2025 Avg Pts"]).sum()
            st.metric("Avg Playoff Score (2025)", f"{total_25:.2f}", f"{total_25 - total_24:.2f} vs 2024")