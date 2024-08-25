"""
Functions that generates random numbers
"""
import random
from website.setup_db import db
from website.models import LotteryNumbers, User, UserNumbers


def generate_normalized_odds():
    probabilities = [random.random() for _ in range(3)]
    
    total = sum(probabilities)
    normalized_probabilities = [p / total for p in probabilities]
    
    odds = [round(1 / p, 2) for p in normalized_probabilities]
    
    return  odds



def generate_five_numbers():
    return random.sample(range(1, 36), 5)

def draw_lottery_numbers():
    numbers = generate_five_numbers()
    lottery_entry = LotteryNumbers(numbers)
    db.session.add(lottery_entry)
    db.session.commit()

def get_latest_lottery_numbers():
    latest_lottery = LotteryNumbers.query.order_by(LotteryNumbers.id.desc()).first()
    if latest_lottery:
        return latest_lottery.get_numbers()
    else:
        return None 

def check_user_numbers_against_lottery():
    latest_lottery_numbers = get_latest_lottery_numbers()
    if not latest_lottery_numbers:
        print("No lottery numbers available for comparison.")
        return []

    all_user_numbers = UserNumbers.query.all()
    winning_users = []

    for user_numbers_entry in all_user_numbers:
        user_numbers = user_numbers_entry.get_numbers()
        if set(user_numbers) == set(latest_lottery_numbers):
            winning_users.append(user_numbers_entry.user_id)
            user = User.query.get(user_numbers_entry.user_id)
            user.balance += 30000
            db.session.commit()

    return winning_users


