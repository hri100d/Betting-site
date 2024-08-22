from datetime import datetime
import json
import dotenv
import os
from flask import jsonify
import requests

from typing import Dict, List, Optional

from .models import *

dotenv.load_dotenv()

football_base_url = os.getenv('URL')

def get_api_key() -> Optional[str]:
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")

    if not api_key:
        raise ValueError("API key is not configured")
    
    return api_key

def get_football_data_request_headers() -> dict:
    api_key = get_api_key()
    headers = {
       'X-Auth-Token': api_key
    }

    return headers

def fetch_football_data(endpoint: str) -> dict:
    url = football_base_url + endpoint
    
    response = requests.get(url, headers=get_football_data_request_headers())
    if response.status_code >= 300:
        raise ValueError(f"Bad response - status code: {response.status_code}")
    
    return response.json()

def create_match_models(motches_data: list[dict]) -> list[Match]:
    return [Match(id=match["id"],
    utc_date=datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%S%z"),
    status=match["status"],
    stage=match["stage"],
    group=match["group"],
    home_team_id=match["homeTeam"]["id"],
    home_team_name = match["homeTeam"]["name"],
    away_team_name = match["awayTeam"]["name"],
    away_team_id=match["awayTeam"]["id"],
    winner=match["score"]["winner"],
    duration=match["score"]["duration"],
    full_time_home=match["score"]["fullTime"]["home"],
    full_time_away=match["score"]["fullTime"]["away"],
    half_time_home=match["score"]["halfTime"]["home"],
    half_time_away=match["score"]["halfTime"]["away"],)
            for match in motches_data]

def create_bet_model(bet_data: dict) -> Bet:
    bet = Bet(
        id=bet_data.get("id"),
        amount=bet_data.get("amount"),
        odd=bet_data.get("odd"),
        date=bet_data.get("date"), 
        status=bet_data.get("status")
    )
    return bet


def create_team_model(team_data: dict) -> Team:
    team = Team(
        id=team_data.get("id"),
        name=team_data.get("name"),
        short_name=team_data.get("short_name"),
        tla=team_data.get("tla"),
        crest=team_data.get("crest"),
        coach_id=team_data.get("coach_id"),  
        formation=team_data.get("formation")
    )
    return team


def create_match_model(match_data: dict) -> Match:
    match = Match(
        id=match_data.get("id"),
        utc_date=match_data.get("utc_date"),
        status=match_data.get("status"),
        stage=match_data.get("stage"),
        group=match_data.get("group"),
        home_team_id=match_data.get("home_team_id"),
        away_team_id=match_data.get("away_team_id"),
        winner=match_data.get("winner"),
        duration=match_data.get("duration"),
        full_time_home=match_data.get("full_time_home"),
        full_time_away=match_data.get("full_time_away"),
        half_time_home=match_data.get("half_time_home"),
        half_time_away=match_data.get("half_time_away")
    )
    return match


def get_match_head2head_by_id(match_id: int) -> Match:
    match = f'{match_id}'
    endpoint =  f"matches/{match}/head2head?limit=10"

    data = fetch_football_data(endpoint)
    return data

def get_all_areas_and_competitions():
    endpoint = "competitions"
    data = fetch_football_data(endpoint)
    return data

def get_matches_by_competition(competiton_code: str) -> list:
    endpoint = f"competitions/{competiton_code}/matches"
    data = fetch_football_data(endpoint)
    return data["matches"]

def get_standings_by_competition(competiton_code: str) -> list:
    endpoint = f"competitions/{competiton_code}/standings"
    data = fetch_football_data(endpoint)
    return data["standings"]

def get_topscorers_by_competition(competiton_code: str) -> list:
    endpoint = f"competitions/{competiton_code}/scorers"
    data = fetch_football_data(endpoint)
    return data["scorers"]

def get_team_by_id(team_id: int) -> dict:
    enpoint = f"teams/{team_id}"
    data = fetch_football_data(enpoint)
    return data