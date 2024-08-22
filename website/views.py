from datetime import datetime
import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import Transaction
from website.fd_interface import get_match_head2head_by_id, get_standings_by_competition, get_team_by_id, get_topscorers_by_competition
from website.setup_db import db
from sqlalchemy.exc import SQLAlchemyError

from website.models import Area, Bet, BetMatch, Competition, Match, Team, User

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


@views.route('/delete/bet/<int:id>', methods=['POST'])
@login_required
def delete_bet(id):
    
    bet_to_delete = Bet.query.get_or_404(id)

    date = request.form.get('date')
    areas = request.form.get('areas')

    if bet_to_delete.user_id != current_user.id:
        flash("You are not authorized to delete this bet!")
        return redirect(url_for('views.home'))

    try:
        db.session.delete(bet_to_delete)
        db.session.commit()
        flash("Bet deleted successfully!")
    except Exception as e:
        db.session.rollback()
        flash("There was a problem deleting the bet!")

    return redirect(url_for('views.home', user=current_user, areas=areas, date=date))


@views.route('/update/bet', methods=['POST'])
@login_required
def place_bet():
    if request.method == 'POST':
        areas = request.form.get('areas') 
        date = request.form.get('date') 

        if 'match_id' in request.form:
            match_id = request.form['match_id']
            odd = float(request.form['odd'])
            winner = request.form['winner']

            match = Match.query.get_or_404(match_id)
            home_team, away_team = None, None
            if match.teams:
                home_team = match.teams[0].short_name
                away_team = match.teams[1].short_name

            bet = Bet.query.filter_by(user_id=current_user.id, status='PENDING').first()
            if not bet:
                bet = Bet(user_id=current_user.id, status='PENDING', odd=1.0)
                db.session.add(bet)
                db.session.commit()

            existing_bet_match = BetMatch.query.filter_by(bet_id=bet.id, match_id=match_id).first()
            if not existing_bet_match:
                bet_match = BetMatch(
                    bet_id=bet.id,
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    winner=winner,
                    odd=odd
                )
                bet.odd *= odd  
                db.session.add(bet_match)
                db.session.commit()

        elif 'amount' in request.form:
            amount = float(request.form['amount'])
            bet = Bet.query.filter_by(user_id=current_user.id, status='PENDING').first()
            
            if bet and bet.bet_matches:
                bet_matches_with_unfinished_matches = BetMatch.query.join(Match).filter(
                    BetMatch.bet_id == bet.id,
                    Match.id == BetMatch.match_id,
                    Match.status != 'FINISHED'
                ).all()

                for bet_match in bet.bet_matches:
                    if bet_match.match.status == 'FINISHED':
                        db.session.delete(bet_match)
                
                remaining_odd = 1.0
                for bet_match in bet.bet_matches:
                    if bet_match.match.status != 'FINISHED':
                        remaining_odd *= bet_match.odd
                
                bet.odd = remaining_odd
                bet.money_placed = amount
                bet.status = 'PLACED'
                bet.win_amount = bet.money_placed * bet.odd
                
                db.session.commit()

        return redirect(url_for('views.home', user=current_user, areas=areas, date=date))

@views.route('/update/bet/match', methods=['POST'])
@login_required
def place_bet_from_match():
    if request.method == 'POST':
        competition_id = request.form.get('competition_id')
        match_id = request.form.get('match_id')

        if match_id:
            odd = float(request.form['odd'])
            winner = request.form['winner']

            match = Match.query.get_or_404(match_id)
            home_team, away_team = None, None
            if match.teams:
                home_team = match.teams[0].short_name
                away_team = match.teams[1].short_name

            bet = Bet.query.filter_by(user_id=current_user.id, status='PENDING').first()
            if not bet:
                bet = Bet(user_id=current_user.id, status='PENDING', odd=1.0)  
                db.session.add(bet)
                db.session.commit()

            existing_bet_match = BetMatch.query.filter_by(bet_id=bet.id, match_id=match_id).first()
            if not existing_bet_match:
                bet_match = BetMatch(
                    bet_id=bet.id,
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    winner=winner,
                    odd=odd
                )
                bet.odd *= odd  
                db.session.add(bet_match)
                db.session.commit()

        elif 'amount' in request.form:
            amount = float(request.form['amount'])
            bet = Bet.query.filter_by(user_id=current_user.id, status='PENDING').first()
            if bet and bet.bet_matches:
                bet.money_placed = amount
                bet.status = 'PLACED'
                bet.win_amount = bet.money_placed * bet.odd
                db.session.commit()

        return redirect(url_for('views.match_details', competition_id=competition_id, match_id=match_id))



@views.route('/delete/betmatch/<int:id>', methods=['POST'])
@login_required
def delete_betmatch(id):
    bet_match_to_delete = BetMatch.query.get_or_404(id)
    bet = Bet.query.get_or_404(bet_match_to_delete.bet_id)

    date = request.form.get('date')
    areas = request.form.get('areas')

    if bet.user_id != current_user.id:
        flash("You are not authorized to delete this bet match!")
        return redirect(url_for('views.home'))

    try:
        db.session.delete(bet_match_to_delete)
        bet.odd /= bet_match_to_delete.odd

        remaining_bet_matches = BetMatch.query.filter_by(bet_id=bet.id).all()
        if not remaining_bet_matches:
            db.session.delete(bet)
        
        db.session.commit()
        flash("Bet match deleted successfully!")

    except Exception as e:
        db.session.rollback()

    return redirect(url_for('views.home', user=current_user, areas=areas, date=date))

@views.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
    
        amount = float(request.form.get('amount'))
        if amount <= 0:
            flash("Deposit amount must be greater than zero.", category="error")
            return redirect(url_for('views.deposit'))
    

        
        current_user.balance += amount
        transaction = Transaction(amount=amount, type='deposit', user_id=current_user.id)
        db.session.add(transaction)
        db.session.commit()

        flash(f"Successfully deposited ${amount}!", category="success")
        
        return redirect(url_for('views.deposit'))

    return render_template('deposit.html', user=current_user)

@views.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            if amount <= 0:
                flash("Withdrawal amount must be greater than zero.", category="error")
                return redirect(url_for('views.withdraw'))
            elif current_user.balance < amount:
                flash("Insufficient funds.", category="error")
                return redirect(url_for('views.withdraw'))
        except (ValueError, TypeError):
            flash("Invalid amount entered.", category="error")
            return redirect(url_for('views.withdraw'))

        try:
            current_user.balance -= amount
            transaction = Transaction(amount=amount, type='withdraw', user_id=current_user.id)
            db.session.add(transaction)
            db.session.commit()

            flash(f"Successfully withdrew ${amount}!", category="success")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing withdrawal: {e}")
            flash("There was an error processing your withdrawal.", category="error")

        return redirect(url_for('views.withdraw'))

    return render_template('withdraw.html', user=current_user)