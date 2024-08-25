"""
Handles routes for showing information for matches, copetitions, matches, bets, teams using the FD API and lottery
"""
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from website.fd_interface import get_match_head2head_by_id, get_standings_by_competition, get_team_by_id, get_topscorers_by_competition

from website.models import Area, Bet, BetMatch, Competition, LotteryNumbers, Match, Team, User, UserNumbers
from .setup_db import db

views = Blueprint('views', __name__, template_folder="../templates/")

@views.route('/', methods=['GET', 'POST'])
def home():
    areas = Area.query.all()
    date = request.args.get('date', datetime.utcnow().date().isoformat())

    return render_template('home.html', user=current_user, areas=areas, date=date)


@views.route('/bets')
@login_required
def bets():
    user_bets = Bet.query.filter_by(user_id=current_user.id).filter(Bet.status != 'PENDING').all()
    
    bet_matches = BetMatch.query.join(Match).filter(BetMatch.bet_id.in_([bet.id for bet in user_bets])).all()

    return render_template('bets.html', user=current_user, bets=user_bets, bet_matches=bet_matches)


@views.route('/competitions/<int:id>', methods=['GET'])
def competition_details(id):
    competition = Competition.query.get_or_404(id)
    standings = get_standings_by_competition(competition.code)
    scorers = get_topscorers_by_competition(competition.code)
    
    date = request.args.get('date', datetime.utcnow().date().isoformat())
    
    filtered_matches = [match for match in competition.matches if match.utc_date.split('T')[0] == date]
    
    return render_template(
        'competition.html',
        user=current_user,
        competition=competition,
        standings=standings,
        scorers=scorers,
        date=date,
        matches=filtered_matches
    )
    
@views.route('/competitions/<int:competition_id>/matches/<int:match_id>', methods=['GET'])
def match_details(competition_id, match_id):
    competition = Competition.query.get_or_404(competition_id)
    
    match = Match.query.filter_by(id=match_id, competition_id=competition_id).first_or_404()
    
    standings = get_standings_by_competition(competition.code)
    data = get_match_head2head_by_id(match_id)
    aggregates = data['aggregates']
    matches = data['matches']
    
    return render_template('match.html', user=current_user, competition=competition, match=match, standings=standings, aggregates=aggregates, matches=matches)

@views.route('/teams/<int:id>')
def team_details(id):
    team_data = get_team_by_id(id)
    area = team_data['area']
    competitions = team_data['runningCompetitions']
    coach = team_data['coach']
    squad = team_data['squad']

    team = Team.query.get(id)  
    if team is None:
        return "Team not found", 404

    matches = team.matches  

    return render_template('team.html',
                           team_data=team_data,
                           user=current_user,
                           area=area,
                           competitions=competitions,
                           coach=coach,
                           squad=squad,
                           matches=matches)


@views.route('/lottery', methods=['GET', 'POST'])
@login_required
def lottery():
    if request.method == 'POST':
        numbers = [request.form.get(f'number{i}') for i in range(1, 6)]
        numbers = list(map(int, numbers))
        
        user_id = current_user.id
        user_numbers = UserNumbers(numbers=numbers, user_id=user_id)
        db.session.add(user_numbers)
        db.session.commit()
        flash('Your numbers have been submitted!', 'success')
        return redirect(url_for('views.lottery'))

    latest_lottery = LotteryNumbers.query.order_by(LotteryNumbers.id.desc()).first()
    winners = []
    if latest_lottery:
        latest_numbers = latest_lottery.get_numbers()
        winners = User.query.join(UserNumbers).filter(
            UserNumbers.numbers == ','.join(map(str, latest_numbers))
        ).all()

    previous_lotteries = LotteryNumbers.query.order_by(LotteryNumbers.id.desc()).all()

    return render_template('lottery.html', user=current_user, winners=winners, previous_lotteries=previous_lotteries)
