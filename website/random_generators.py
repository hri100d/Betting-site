import random
from website.setup_db import db
from website.models import LotteryNumbers


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

