from pathlib import Path
import json

def load_questions():
    """Загружает вопросы из JSON"""
    with open('data/questions.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_character_count():
    """Возвращает количество персонажей"""
    return len(list(Path('data/characters').glob('*.json')))