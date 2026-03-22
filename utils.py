import random
from config import MAX_WARNS


def check_bad_words(text, banned_words):
    """Проверяет текст на наличие запрещенных слов"""
    if not text or not banned_words:
        return False

    text_lower = text.lower()
    for word in banned_words:
        if word in text_lower:
            return True
    return False


def roll_dice():
    """Бросок кубика (возвращает число от 1 до 6)"""
    return random.randint(1, 6)


def play_slots():
    """Игровой автомат. Возвращает (комбинация, выигрыш_множитель)"""
    symbols = ['🍒', '🍋', '🍊', '7️⃣', '💎', 'BAR']
    result = [random.choice(symbols) for _ in range(3)]

    # Проверка выигрышных комбинаций
    if result[0] == result[1] == result[2]:
        if result[0] == '7️⃣':
            multiplier = 10  # Джекпот за 777
        elif result[0] == '💎':
            multiplier = 7
        elif result[0] == 'BAR':
            multiplier = 5
        else:
            multiplier = 3
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        multiplier = 2  # Два одинаковых
    else:
        multiplier = 0  # Проигрыш

    return result, multiplier


def format_number(num):
    """Форматирует число с разделением тысяч"""
    return f"{num:,}".replace(",", " ")

"""
git init
git add .
git commit -m "Initial commit: Telegram admin bot"
git branch -M main
git remote add origin https://github.com/ТВОЙ_ЛОГИН/НАЗВАНИЕ_РЕПО.git
git push -u origin main"""