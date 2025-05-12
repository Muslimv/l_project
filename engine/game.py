import json
import math
import random
from pathlib import Path
from telegram import ReplyKeyboardMarkup

class GameSession:
    active_sessions = {}

    @classmethod
    def _load_characters(cls):
        """Загружает всех персонажей из папки characters"""
        characters = []
        for file in Path('data/characters').glob('*.json'):
            with open(file, 'r', encoding='utf-8') as f:
                characters.append(json.load(f))
        return characters

    @classmethod
    async def start_game(cls, update, context):
        """Начинает новую игру"""
        user_id = update.effective_user.id
        cls.active_sessions[user_id] = {
            'remaining_chars': cls._load_characters(),
            'asked_questions': set()
        }
        await cls._ask_question(update, context)

    @classmethod
    async def _ask_question(cls, update, context):
        """Задает следующий вопрос"""
        user_id = update.effective_user.id
        session = cls.active_sessions[user_id]
        
        question = cls._select_best_question(session)
        session['current_question'] = question['id']
        
        await update.message.reply_text(
            question['text'],
            reply_markup=ReplyKeyboardMarkup(
                [['Да', 'Нет', 'Не знаю']],
                one_time_keyboard=True
            )
        )

    @classmethod
    def _select_best_question(cls, session):
        """Выбирает оптимальный вопрос через энтропию"""
        with open('data/questions.json', 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        best_q = None
        max_score = -1
        
        for q_id, q_data in questions.items():
            if q_id in session['asked_questions']:
                continue
                
            yes = sum(1 for c in session['remaining_chars'] if c['traits'].get(q_id) is True)
            no = len(session['remaining_chars']) - yes
            score = cls._calculate_question_score(yes, no)
            
            if score > max_score:
                max_score = score
                best_q = {'id': q_id, 'text': q_data['text']}
        
        return best_q or random.choice(list(questions.items()))

    @staticmethod
    def _calculate_question_score(yes, no):
        """Рассчитывает информативность вопроса"""
        total = yes + no
        if total == 0: return 0
        
        p_yes = yes / total
        p_no = no / total
        
        entropy = 0
        if p_yes > 0: entropy -= p_yes * math.log2(p_yes)
        if p_no > 0: entropy -= p_no * math.log2(p_no)
            
        return entropy

    @classmethod
    async def handle_answer(cls, update, context):
        """Обрабатывает ответ пользователя"""
        user_id = update.effective_user.id
        session = cls.active_sessions.get(user_id)
        
        if not session:
            await update.message.reply_text("Начните игру с /play")
            return
            
        answer = update.message.text
        q_id = session['current_question']
        
        # Фильтрация персонажей
        if answer == 'Да':
            session['remaining_chars'] = [
                c for c in session['remaining_chars'] 
                if c['traits'].get(q_id) is True
            ]
        elif answer == 'Нет':
            session['remaining_chars'] = [
                c for c in session['remaining_chars'] 
                if c['traits'].get(q_id) is False
            ]
            
        session['asked_questions'].add(q_id)
        
        # Проверка результата
        if len(session['remaining_chars']) == 1:
            await cls._send_character(update, session['remaining_chars'][0])
            del cls.active_sessions[user_id]
        elif not session['remaining_chars']:
            await update.message.reply_text("Я сдаюсь! Кто это был? Напишите /learn чтобы научить меня")
            del cls.active_sessions[user_id]
        else:
            await cls._ask_question(update, context)

    @staticmethod
    async def _send_character(update, character):
        """Отправляет информацию о персонаже"""
        text = f"🎉 Это... {character['name']}!\n\nХарактеристики:\n"
        text += "\n".join(f"- {k}: {'Да' if v else 'Нет'}" for k,v in character['traits'].items())
        await update.message.reply_text(text)