import pandas as pd
from sleeper_api import *

def get_season_standings(league_id):
    """
    Get standings for a single season.
    Returns: DataFrame with team standings for that season
    """
    all_rosters = get_all_rosters(league_id)
    league_users = get_league_users(league_id)
    league_info = get_league_info(league_id)
    season_year = league_info.get('season', 'Unknown')
    
    teams_data = []
    for roster in all_rosters:
        owner_id = roster.get('owner_id')
        owner_info = next((u for u in league_users if u.get('user_id') == owner_id), {})
        
        teams_data.append({
            'season': season_year,
            'user_id': owner_id,
            'team_name': owner_info.get('metadata', {}).get('team_name', owner_info.get('display_name')),
            'username': owner_info.get('display_name', 'N/A'),
            'wins': roster.get('settings', {}).get('wins', 0),
            'losses': roster.get('settings', {}).get('losses', 0),
            'ties': roster.get('settings', {}).get('ties', 0),
            'fpts': roster.get('settings', {}).get('fpts', 0),
            'fpts_decimal': roster.get('settings', {}).get('fpts_decimal', 0),
            'ppts': roster.get('settings', {}).get('ppts', 0),
            'ppts_decimal': roster.get('settings', {}).get('ppts_decimal', 0),
            'total_moves': roster.get('settings', {}).get('total_moves', 0),
            'waiver_position': roster.get('settings', {}).get('waiver_position', 'N/A'),
            'waiver_budget_used': roster.get('settings', {}).get('waiver_budget_used', 0),
        })
    
    return pd.DataFrame(teams_data)


def get_franchise_history(league_ids, username):
    """
    Aggregate stats for a specific user across multiple seasons.
    
    Args:
        league_ids: List of league IDs (e.g., ['2024_id', '2025_id'])
        username: Sleeper username
    
    Returns: Dictionary with aggregated franchise stats
    """
    user_info = get_user_info(username)
    user_id = user_info.get('user_id')
    
    total_wins = 0
    total_losses = 0
    total_ties = 0
    total_fpts = 0
    total_ppts = 0
    seasons_played = 0
    playoff_appearances = 0
    championships = 0
    
    season_records = []
    
    for league_id in league_ids:
        try:
            rosters = get_all_rosters(league_id)
            league_info = get_league_info(league_id)
            season = league_info.get('season', 'Unknown')
            
            # Find user's roster for this season
            user_roster = next((r for r in rosters if r.get('owner_id') == user_id), None)
            
            if user_roster:
                settings = user_roster.get('settings', {})
                wins = settings.get('wins', 0)
                losses = settings.get('losses', 0)
                ties = settings.get('ties', 0)
                fpts = settings.get('fpts', 0) + settings.get('fpts_decimal', 0) / 100
                ppts = settings.get('ppts', 0) + settings.get('ppts_decimal', 0) / 100
                
                total_wins += wins
                total_losses += losses
                total_ties += ties
                total_fpts += fpts
                total_ppts += ppts
                seasons_played += 1
                
                # Check for playoff appearance (typically top 6 in standings)
                all_standings = sorted(rosters, 
                                     key=lambda x: x.get('settings', {}).get('wins', 0), 
                                     reverse=True)
                user_position = next((i for i, r in enumerate(all_standings) 
                                    if r.get('owner_id') == user_id), None)
                
                if user_position is not None and user_position < 6:  # Adjust based on playoff structure
                    playoff_appearances += 1
                
                # Check for championship (would need playoff bracket data)
                # For now, we'll leave this for manual entry or future enhancement
                
                season_records.append({
                    'season': season,
                    'wins': wins,
                    'losses': losses,
                    'ties': ties,
                    'fpts': round(fpts, 2),
                    'ppts': round(ppts, 2),
                    'finish': user_position + 1 if user_position is not None else 'N/A'
                })
        
        except Exception as e:
            print(f"Error processing league {league_id}: {e}")
            continue
    
    return {
        'total_wins': total_wins,
        'total_losses': total_losses,
        'total_ties': total_ties,
        'total_fpts': round(total_fpts, 2),
        'total_ppts': round(total_ppts, 2),
        'seasons_played': seasons_played,
        'playoff_appearances': playoff_appearances,
        'championships': championships,
        'win_percentage': round(total_wins / (total_wins + total_losses) * 100, 1) if (total_wins + total_losses) > 0 else 0,
        'avg_fpts_per_season': round(total_fpts / seasons_played, 2) if seasons_played > 0 else 0,
        'season_records': season_records
    }


def get_all_time_standings(league_ids):
    """
    Get all-time standings across multiple seasons.
    
    Args:
        league_ids: List of league IDs
    
    Returns: DataFrame with aggregated standings by user
    """
    all_seasons_data = []
    
    for league_id in league_ids:
        try:
            season_df = get_season_standings(league_id)
            all_seasons_data.append(season_df)
        except Exception as e:
            print(f"Error processing league {league_id}: {e}")
            continue
    
    if not all_seasons_data:
        return pd.DataFrame()
    
    # Combine all seasons
    combined_df = pd.concat(all_seasons_data, ignore_index=True)
    
    # Group by user and aggregate
    aggregated = combined_df.groupby(['username']).agg({
        'wins': 'sum',
        'losses': 'sum',
        'fpts': 'sum',
        'ppts': 'sum',
        'season': 'count',
    }).reset_index()
    
    aggregated.columns = ['Owner', 'Total Wins', 'Total Losses', 
                          'Total PF', 'Total Max PF', 'Seasons']
    
    # Calculate win percentage
    aggregated['Win Pct (%)'] = (aggregated['Total Wins'] / 
                             (aggregated['Total Wins'] + aggregated['Total Losses']) * 100).round(1)
    
    # Calculate average points per season
    aggregated['Avg PF Per Season'] = (aggregated['Total PF'] / aggregated['Seasons']).round(2)
    
    # Sort by total wins
    aggregated = aggregated.sort_values('Total Wins', ascending=False)
    
    return aggregated


def get_season_by_season_records(league_id):
    """
    Get formatted standings for a single season with calculated fields.
    
    Args:
        league_id: Single league ID
    
    Returns: DataFrame with standings for that season
    """
    # Get raw season data
    season_df = get_season_standings(league_id)
    
    if season_df.empty:
        return pd.DataFrame()
    
    # Calculate total points (including decimals)
    season_df['total_fpts'] = season_df['fpts'] + season_df['fpts_decimal'] / 100
    season_df['total_ppts'] = season_df['ppts'] + season_df['ppts_decimal'] / 100
    
    # Create formatted output DataFrame
    result_df = pd.DataFrame({
        'Team Name': season_df['team_name'],
        'Owner': season_df['username'],
        'Wins': season_df['wins'],
        'Losses': season_df['losses'],
        'PF': season_df['total_fpts'].round(2),
        'Max PF': season_df['total_ppts'].round(2),
        'Total Moves': season_df['total_moves'],
    })
    
    # Calculate win percentage
    result_df['Win %'] = ((result_df['Wins'] / 
                          (result_df['Wins'] + result_df['Losses']) * 100)
                          .round(1))
    
    # Calculate point differential
    result_df['Lineup Accuracy (%)'] = ((result_df['PF'] / result_df['Max PF']) * 100).round(2)
    
    # Sort by wins (descending), then by points for
    result_df = result_df.sort_values(['Wins', 'Max PF'], ascending=[False, False])
    
    # Add rank column
    result_df.insert(0, 'Rank', range(1, len(result_df) + 1))
    
    return result_df


def get_head_to_head_record(league_ids, user_id_1, user_id_2):
    """
    Get head-to-head record between two users across all seasons.
    
    Args:
        league_ids: List of league IDs
        user_id_1: First user's Sleeper user_id
        user_id_2: Second user's Sleeper user_id
    
    Returns: Dictionary with head-to-head stats
    """
    # This would require matchup data from each week
    # Placeholder for future implementation
    return {
        'user_1_wins': 0,
        'user_2_wins': 0,
        'ties': 0,
        'total_matchups': 0
    }