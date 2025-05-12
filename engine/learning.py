import json
import re
from pathlib import Path
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from typing import Dict, Any

class LearningMode:
    """Режим обучения новым персонажам"""
    
    # Хранит состояние обучения для каждого пользователя
    learning_sessions: Dict[int, Dict[str, Any]] = {}

    @classmethod
    async def start_learning(cls, update, context: ContextTypes.DEFAULT_TYPE):
        """Начинает процесс обучения новому персонажу"""
        user_id = update.effective_user.id
        
        cls.learning_sessions[user_id] = {
            'state': 'awaiting_name',
            'character': {
                'name': '',
                'traits': {},
                'image_path': None
            }
        }

        await update.message.reply_text(
            "🔍 Давайте научим меня новому персонажу!\n"
            "Как его зовут?",
            reply_markup=ReplyKeyboardRemove()
        )

    @classmethod
    async def handle_learning(cls, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает все сообщения в режиме обучения"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Проверяем, есть ли активная сессия обучения
        if user_id not in cls.learning_sessions:
            await update.message.reply_text(
                "Чтобы начать обучение, отправьте /learn",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        session = cls.learning_sessions[user_id]
        state = session['state']
        character = session['character']

        # Обработка состояний по порядку
        if state == 'awaiting_name':
            await cls._handle_name(update, character)
            session['state'] = 'awaiting_question'
            
        elif state == 'awaiting_question':
            if text.lower() in ['готово', 'закончить']:
                await cls._finish_learning(update, character)
                del cls.learning_sessions[user_id]
            else:
                await cls._handle_new_question(update, session, text)
                
        elif state == 'awaiting_answer':
            await cls._handle_answer(update, session, text)
            session['state'] = 'awaiting_question'

    @staticmethod
    async def _handle_name(update, character_data: Dict[str, Any]):
        """Обрабатывает ввод имени персонажа"""
        name = update.message.text.strip()
        
        # Валидация имени
        if not re.match(r"^[А-Яа-яA-Za-z\s]{2,30}$", name):
            await update.message.reply_text(
                "❌ Имя должно содержать только буквы и пробелы (2-30 символов)\n"
                "Попробуйте еще раз:"
            )
            return

        character_data['name'] = name
        await update.message.reply_text(
            f"👌 Отлично, персонаж '{name}'!\n\n"
            "Теперь задайте вопрос о персонаже, например:\n"
            "\"Это человек?\"\n"
            "Или напишите \"Готово\" чтобы завершить",
            reply_markup=ReplyKeyboardMarkup([['Готово']], one_time_keyboard=True)
        )

    @staticmethod
    async def _handle_new_question(update, session_data: Dict[str, Any], question_text: str):
        """Обрабатывает новый вопрос о персонаже"""
        question = question_text.strip().rstrip('?')
        
        # Нормализация вопроса
        question = question[0].upper() + question[1:]
        if not question.endswith('?'):
            question += '?'
            
        session_data['current_question'] = question
        session_data['state'] = 'awaiting_answer'
        
        await update.message.reply_text(
            f"❓ Вопрос: {question}\n"
            "Какой ответ? (Да/Нет)",
            reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True)
        )

    @staticmethod
    async def _handle_answer(update, session_data: Dict[str, Any], answer: str):
        """Сохраняет ответ на текущий вопрос"""
        question = session_data['current_question']
        character = session_data['character']
        
        # Преобразуем ответ в boolean
        is_yes = answer.lower() in ['да', 'yes']
        character['traits'][question] = is_yes
        
        await update.message.reply_text(
            f"✅ Запомнил: {question} → {'Да' if is_yes else 'Нет'}\n\n"
            "Задайте следующий вопрос или напишите \"Готово\"",
            reply_markup=ReplyKeyboardMarkup([['Готово']], one_time_keyboard=True)
        )

    @staticmethod
    async def _finish_learning(update, character_data: Dict[str, Any]):
        """Завершает процесс обучения и сохраняет персонажа"""
        try:
            # Сохранение в формате JSON
            filename = f"data/characters/{character_data['name'].lower().replace(' ', '_')}.json"
            
            # Создаем директорию, если ее нет
            Path('data/characters').mkdir(exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, ensure_ascii=False, indent=2)
                
            await update.message.reply_text(
                f"🎉 Персонаж '{character_data['name']}' успешно сохранен!\n"
                f"Всего характеристик: {len(character_data['traits'])}\n\n"
                "Можете начать новую игру с /play",
                reply_markup=ReplyKeyboardRemove()
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка при сохранении: {str(e)}\n"
                "Попробуйте еще раз позже",
                reply_markup=ReplyKeyboardRemove()
            )