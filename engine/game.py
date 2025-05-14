import json
import math
import random
from pathlib import Path
from telegram import ReplyKeyboardMarkup

class GameSession:
    active_sessions = {}  # Словарь активных сессий пользователей

    @classmethod
    def _load_characters(cls):
        """Загружает всех персонажей из папки characters"""
        characters = []
        for file in Path('data/characters').glob('*.json'):
            with open(file, 'r', encoding='utf-8') as f:
                characters.append(json.load(f))  # Добавляем загруженного персонажа в список
        return characters

    @classmethod
    async def start_game(cls, update, context):
        """Начинает новую игру"""
        user_id = update.effective_user.id  # Получаем ID пользователя
        # Создаем новую сессию для этого пользователя
        cls.active_sessions[user_id] = {
            'remaining_chars': cls._load_characters(),  # Загружаем персонажей
            'asked_questions': set()  # Устанавливаем множество заданных вопросов
        }
        await cls._ask_question(update, context)  # Задаем первый вопрос

    @classmethod
    async def _ask_question(cls, update, context):
        """Задает следующий вопрос"""
        user_id = update.effective_user.id
        session = cls.active_sessions[user_id]  # Получаем сессию пользователя
        
        question = cls._select_best_question(session)  # Выбираем лучший вопрос
        session['current_question'] = question['id']  # Сохраняем ID текущего вопроса
        
        # Отправляем вопрос пользователю с вариантами ответов
        await update.message.reply_text(
            question['text'],
            reply_markup=ReplyKeyboardMarkup(
                [['Да', 'Нет', 'Не знаю']],  # Кнопки для ответов
                one_time_keyboard=True  # Убираем клавиатуру после ответа
            )
        )

    @classmethod
    def _select_best_question(cls, session):
        """Выбирает оптимальный вопрос через энтропию"""
        with open('data/questions.json', 'r', encoding='utf-8') as f:
            questions = json.load(f)  # Загружаем вопросы
        
        best_q = None
        max_score = -1
        
        for q_id, q_data in questions.items():
            if q_id in session['asked_questions']:
                continue  # Пропускаем уже заданные вопросы
                
            # Считаем количество "Да" и "Нет" для данного вопроса
            yes = sum(1 for c in session['remaining_chars'] if c['traits'].get(q_id) is True)
            no = len(session['remaining_chars']) - yes
            
            # Рассчитываем информативность вопроса
            score = cls._calculate_question_score(yes, no)
            
            if score > max_score:  # Если вопрос лучше предыдущего
                max_score = score
                best_q = {'id': q_id, 'text': q_data['text']}
        
        return best_q or random.choice(list(questions.items()))  # Возвращаем лучший вопрос или случайный

    @staticmethod
    def _calculate_question_score(yes, no):
        """Рассчитывает информативность вопроса"""
        total = yes + no
        if total == 0: return 0  # Если вопросов нет, возвращаем 0
        
        p_yes = yes / total  # Вероятность "Да"
        p_no = no / total    # Вероятность "Нет"
        
        # Вычисляем энтропию
        entropy = 0
        if p_yes > 0: entropy -= p_yes * math.log2(p_yes)  # Добавляем вклад вероятности "Да"
        if p_no > 0: entropy -= p_no * math.log2(p_no)    # Добавляем вклад вероятности "Нет"
        
        return entropy  # Возвращаем значение энтропии

    @classmethod
    async def handle_answer(cls, update, context):
        """Обрабатывает ответ пользователя"""
        user_id = update.effective_user.id
        session = cls.active_sessions.get(user_id)  # Получаем сессию пользователя
        
        if not session:
            await update.message.reply_text("Начните игру с /play")  # Если сессии нет, предложим начать игру
            return
            
        answer = update.message.text  # Получаем ответ пользователя
        q_id = session['current_question']  # Получаем ID текущего вопроса
        
        # Фильтрация оставшихся персонажей на основе ответа
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
        
        session['asked_questions'].add(q_id)  # Добавляем заданный вопрос в множество
        
        # Проверка результата
        if len(session['remaining_chars']) == 1:  # Если остался только один персонаж
            await cls._send_character(update, session['remaining_chars'][0])  # Отправляем информацию о персонаже
            del cls.active_sessions[user_id]  # Удаляем сессию пользователя
        elif not session['remaining_chars']:  # Если не осталось персонажей
            await update.message.reply_text("Я сдаюсь! Кто это был? Напишите /learn чтобы научить меня")
            del cls.active_sessions[user_id]  # Удаляем сессию пользователя
        else:
            await cls._ask_question(update, context)  # Задаем следующий вопрос

    @staticmethod
    async def _send_character(update, character):
        """Отправляет информацию о персонаже"""
        text = f"🎉 Это... {character['name']}!\n\nХарактеристики:\n"
        text += "\n".join(f"- {k}: {'Да' if v else 'Нет'}" for k,v in character['traits'].items())  # Форматируем текст с характеристиками
        await update.message.reply_text(text)  # Отправляем пользователю сообщение с информацией о персонаже