"""
Handles routes for transaction
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from website.setup_db import db
from website.models import Transaction

transactions = Blueprint('transactions', __name__, template_folder="../templates")

@transactions.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        amount = request.form.get('amount')

        try:
            amount = float(amount)
            
            if amount < 10:
                flash("Minimum deposit is $10", category="error")
                return redirect(url_for('transactions.deposit'))

        except ValueError:
            flash("Invalid amount entered.", category="error")
            return redirect(url_for('transactions.deposit'))

        try:
            transaction = Transaction(amount=amount, type='deposit', user_id=current_user.id)

            current_user.balance += amount

            db.session.add(transaction)
            db.session.commit()

            flash("Deposit successful!", category="success")
        except SQLAlchemyError as e:
            db.session.rollback() 
            current_app.logger.error(f"Error processing deposit: {e}")
            flash("There was an error processing your deposit.", category="error")

        return redirect(url_for('transactions.deposit'))

    return render_template('deposit.html', user=current_user)


@transactions.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))

            if amount <= 0:
                flash("Withdrawal amount must be greater than zero.", category="error")
                return redirect(url_for('transactions.withdraw'))

            elif current_user.balance < amount:
                flash("Insufficient funds.", category="error")
                return redirect(url_for('transactions.withdraw'))

        except (ValueError, TypeError):
            flash("Invalid amount entered.", category="error")
            return redirect(url_for('transactions.withdraw'))

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

        return redirect(url_for('transactions.withdraw'))

    return render_template('withdraw.html', user=current_user)
