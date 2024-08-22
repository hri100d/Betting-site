from datetime import datetime
import json
import random
import dotenv
import os
from flask import app, jsonify
import requests

from typing import Optional

from website.fd_interface import get_match_head2head_by_id, get_team_by_id
from website.models import Area, Competition, Team
from website.setup_db import db



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





team_data = get_team_by_id('90')
    
print(team_data)