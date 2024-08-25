"""
Functions that need to run endlessly while the web application is working and setting up scheduler for the web application
"""
import time
from sqlalchemy.orm import joinedload
from flask import Flask
from flask_apscheduler import APScheduler
from website.fd_interface import create_match_model, create_team_model, get_all_areas_and_competitions, get_matches_by_competition, update_match_details, update_or_create_team
from website.models import Area, Bet, BetMatch, Competition, Match, Team
from website.random_generators import draw_lottery_numbers, generate_normalized_odds
from website.setup_db import db

def update_bet_status():
    bets = Bet.query.options(joinedload(Bet.bet_matches).joinedload(BetMatch.match)).filter(Bet.status != 'PENDING').all()

    for bet in bets:
        all_matches_finished = all(bet_match.match.status == 'FINISHED' for bet_match in bet.bet_matches)
        
        if all_matches_finished:
            user_won = True
            for bet_match in bet.bet_matches:
                match = bet_match.match
                if bet_match.winner != match.winner:
                    user_won = False
                    break

            bet.status = 'FINISHED'
            bet.user_won = user_won
            
            db.session.commit()

def sync_areas_and_competitions():
    data = get_all_areas_and_competitions()
    for competition_data in data['competitions']:
        area_data = competition_data.get('area')

        if area_data:
            area = Area.query.get(area_data['id'])
            if area:
                area.name = area_data['name']
                area.code = area_data.get('code')
                area.flag = area_data.get('flag')
                db.session.add(area)  
            else:
                new_area = Area(
                    id=area_data['id'],
                    name=area_data['name'],
                    code=area_data.get('code'),
                    flag=area_data.get('flag')
                )
                db.session.add(new_area) 

        competition = Competition.query.get(competition_data['id'])
        if competition:
            competition.name = competition_data['name']
            competition.code = competition_data.get('code')
            competition.type = competition_data.get('type')
            competition.emblem = competition_data.get('emblem')
            if area_data:
                competition.area_id = area_data['id']
            db.session.add(competition)  
        else:
            new_competition = Competition(
                id=competition_data['id'],
                name=competition_data['name'],
                code=competition_data.get('code'),
                type=competition_data.get('type'),
                emblem=competition_data.get('emblem'),
                area_id=area_data['id'] if area_data else None
            )
            db.session.add(new_competition)  

    db.session.commit()

def sync_matches_and_teams():
    competitions = Competition.query.all()

    for i, competition in enumerate(competitions):
        data = get_matches_by_competition(competition.code)

        for match_data in data:
            odds = generate_normalized_odds()

            home_team_data = match_data['homeTeam']
            away_team_data = match_data['awayTeam']

            home_team = Team.query.get(home_team_data['id'])
            if not home_team:
                home_team = create_team_model(home_team_data)
                db.session.add(home_team)
            else:
                update_or_create_team(home_team, home_team_data)

            away_team = Team.query.get(away_team_data['id'])
            if not away_team:
                away_team = create_team_model(away_team_data)
                db.session.add(away_team)
            else:
                update_or_create_team(away_team, away_team_data)

            match = Match.query.get(match_data['id'])
            if not match:
                match = create_match_model(match_data)
                db.session.add(match)
            else:
                update_match_details(match, match_data, competition.id, odds)

            if home_team not in match.teams:
                match.teams.append(home_team)

            if away_team not in match.teams:
                match.teams.append(away_team)

            if home_team not in competition.teams:
                competition.teams.append(home_team)

            if away_team not in competition.teams:
                competition.teams.append(away_team)

        db.session.commit()

        if i < len(competitions) - 1: 
            time.sleep(10)

def sync_areas_and_copmetitions_with_app_context(app: Flask):
    with app.app_context():
        sync_areas_and_competitions()

def sync_matches_and_teams_with_app_context(app: Flask):
    with app.app_context():
        sync_matches_and_teams()

def draw_lottery_numbers_with_app_context(app: Flask):
    with app.app_context():
        draw_lottery_numbers()

def update_bet_status_with_app_context(app: Flask):
    with app.app_context():
        update_bet_status()
    

def init_scheduler(app: Flask):
    sched = APScheduler()
    sched.init_app(app)
    sched.add_job(id='Job1', func=lambda: sync_areas_and_copmetitions_with_app_context(app), trigger='interval', seconds=800)
    sched.add_job(id='Job2', func=lambda: sync_matches_and_teams_with_app_context(app), trigger='interval', seconds=800)
    sched.add_job(id='Job3', func=lambda: update_bet_status_with_app_context(app), trigger='interval', seconds=10)
    sched.add_job(id='Job4', func=lambda: draw_lottery_numbers_with_app_context(app), trigger='interval', min=10080) # once a week
    sched.start()
