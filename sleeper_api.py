import streamlit as st
import requests
import pandas as pd

@st.cache_data(ttl=86400)
def get_players():
    """Pull in all players from Sleeper API"""
    return requests.get("https://api.sleeper.app/v1/players/nfl").json()

def get_user_info(username):
    """Get user information by username"""
    return requests.get(f"https://api.sleeper.app/v1/user/{username}").json()

def get_league_info(league_id):
    """Get league information"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}").json()

def get_all_rosters(league_id):
    """Get all rosters in the league"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}/rosters").json()

def get_my_roster(league_id, username):
    """Get my full roster object from Sleeper"""
    rosters = get_all_rosters(league_id)
    user = get_user_info(username)
    user_id = user["user_id"]
    my_roster = next(r for r in rosters if r["owner_id"] == user_id)
    return my_roster

def get_my_roster_dataframe(league_id, username):
    """
    Get my roster as a comprehensive DataFrame with all available player info.
    Returns: pandas DataFrame with all Sleeper API player fields
    """
    # Get roster and all players
    my_roster = get_my_roster(league_id, username)
    all_players = get_players()
    player_ids = my_roster.get('players', [])
    
    roster_data = []
    
    for player_id in player_ids:
        if player_id in all_players:
            player = all_players[player_id]
            
            # Extract ALL available fields from Sleeper API
            player_data = {
                # Identity
                'player_id': player.get('player_id', player_id),
                'first_name': player.get('first_name', ''),
                'last_name': player.get('last_name', ''),
                'full_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip() or player_id,
                
                # Position & Team
                'position': player.get('position'),
                'team': player.get('team'),
                'fantasy_positions': player.get('fantasy_positions'),
                'depth_chart_position': player.get('depth_chart_position'),
                'depth_chart_order': player.get('depth_chart_order'),
                
                # Status
                'status': player.get('status'),
                'active': player.get('active'),
                'injury_status': player.get('injury_status'),
                'injury_body_part': player.get('injury_body_part'),
                'injury_notes': player.get('injury_notes'),
                'injury_start_date': player.get('injury_start_date'),
                'practice_participation': player.get('practice_participation'),
                
                # Physical
                'number': player.get('number'),
                'age': player.get('age'),
                'height': player.get('height'),
                'weight': player.get('weight'),
                
                # Background
                'college': player.get('college'),
                'high_school': player.get('high_school'),
                'years_exp': player.get('years_exp'),
                'birth_date': player.get('birth_date'),
                'birth_city': player.get('birth_city'),
                'birth_state': player.get('birth_state'),
                'birth_country': player.get('birth_country'),
                
                # Search Fields
                'search_first_name': player.get('search_first_name'),
                'search_last_name': player.get('search_last_name'),
                'search_full_name': player.get('search_full_name'),
                'search_rank': player.get('search_rank'),
                
                # IDs
                'espn_id': player.get('espn_id'),
                'fantasy_data_id': player.get('fantasy_data_id'),
                'gsis_id': player.get('gsis_id'),
            }
            
            roster_data.append(player_data)
    
    # Create DataFrame
    df = pd.DataFrame(roster_data).sort_values('search_rank')
    
    return df

def get_league_users(league_id):
    """Get all users in the league"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}/users").json()

def get_matchups(league_id, week):
    """Get matchups for a specific week"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}").json()

def get_transactions(league_id, week):
    """Get transactions for a specific week"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}/transactions/{week}").json()

def get_traded_picks(league_id):
    """Get all traded draft picks"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}/traded_picks").json()

def get_playoff_bracket(league_id):
    """Get playoff bracket if playoffs have started"""
    return requests.get(f"https://api.sleeper.app/v1/league/{league_id}/winners_bracket").json()

def get_nfl_state():
    """Get current state of NFL season"""
    return requests.get("https://api.sleeper.app/v1/state/nfl").json()