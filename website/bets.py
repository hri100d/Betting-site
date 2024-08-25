"""
Handles routes for bets
"""
from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from website.setup_db import db
from website.models import Bet, BetMatch, Match

bets = Blueprint('bets', __name__, template_folder="../templates")


@bets.route('/delete/bet/<int:id>', methods=['POST'])
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


@bets.route('/update/bet', methods=['POST'])
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

                if current_user.balance < amount:
                    flash('You do not have enough balance to place this bet.', 'error')
                    return redirect(url_for('views.home', user=current_user, areas=areas, date=date))
                
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

                current_user.balance -= amount
                
                db.session.commit()

        return redirect(url_for('views.home', user=current_user, areas=areas, date=date))

@bets.route('/update/bet/match', methods=['POST'])
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



@bets.route('/delete/betmatch/<int:id>', methods=['POST'])
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