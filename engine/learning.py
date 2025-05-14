import json
import re
from pathlib import Path
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from typing import Dict, Any


class LearningMode:
    """В этом классе алгоритм обучения бота новым персонажам"""
    
    # Здесь будет хранить все активные сессии обучения
    # Ключ - ID пользователя, значение - его текущий прогресс
    learning_sessions: Dict[int, Dict[str, Any]] = {}

    @classmethod
    async def start_learning(cls, update, context: ContextTypes.DEFAULT_TYPE):
        """Пользователь нажал /learn - обучение новым персонажам"""
        user_id = update.effective_user.id
        
        # Создает новую сессию с чистым листом
        cls.learning_sessions[user_id] = {
            'state': 'awaiting_name',  # Сначала спросим имя
            'character': {             # Здесь будем собирать данные
                'name': '',           # Как зовут персонажа
                'traits': {},         # Его характеристики
                'image_path': None    # Можно добавить картинку потом
            }
        }

        # Просит пользователя ввести имя персонажа
        await update.message.reply_text(
            "🔍 Давай создадим нового персонажа! Как его зовут?",
            reply_markup=ReplyKeyboardRemove()  # Убирает клавиатуру
        )

    @classmethod
    async def handle_learning(cls, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает все, что пишет пользователь в режиме обучения"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Если пользователь не начинал обучение, напомнит как это сделать
        if user_id not in cls.learning_sessions:
            await update.message.reply_text(
                "Хочешь научить меня новому персонажу? Напиши /learn",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        session = cls.learning_sessions[user_id]
        state = session['state']  # Текущий этап обучения
        character = session['character']  # То, что уже узнали

        # Разбираемся, на каком этапе мы находимся
        if state == 'awaiting_name':
            # Пользователь должен ввести имя персонажа
            await cls._handle_name(update, character)
            session['state'] = 'awaiting_question'  # Переходит к вопросам
            
        elif state == 'awaiting_question':
            # Пользователь может либо добавить вопрос, либо закончить
            if text.lower() in ['готово', 'закончить']:
                await cls._finish_learning(update, character)
                del cls.learning_sessions[user_id]  # Завершает сессию
            else:
                await cls._handle_new_question(update, session, text)
                
        elif state == 'awaiting_answer':
            # Пользователь отвечает на вопрос (Да/Нет)
            await cls._handle_answer(update, session, text)
            session['state'] = 'awaiting_question'  # Возвращается к вопросам

    @staticmethod
    async def _handle_name(update, character_data: Dict[str, Any]):
        """Проверяет и сохраняет имя персонажа"""
        name = update.message.text.strip()
        
        # Имя должно быть нормальным - только буквы и пробелы
        if not re.match(r"^[А-Яа-яA-Za-z\s]{2,30}$", name):
            await update.message.reply_text(
                "❌ Имя должно содержать только буквы (2-30 символов)\n"
                "Давай попробуем еще раз:"
            )
            return

        # Сохраняет имя и переходит к следующему шагу
        character_data['name'] = name
        await update.message.reply_text(
            f"👌 Отлично, персонаж '{name}'!\n\n"
            "Теперь задай вопрос о персонаже, например:\n"
            "\"Это человек?\"\n"
            "Или напиши \"Готово\" чтобы закончить",
            reply_markup=ReplyKeyboardMarkup([['Готово']], one_time_keyboard=True)
        )

    @staticmethod
    async def _handle_new_question(update, session_data: Dict[str, Any], question_text: str):
        """Добавляет новый вопрос о персонаже"""
        question = question_text.strip().rstrip('?')
        
        # Делает вопрос так: первая буква заглавная, в конце вопрос
        question = question[0].upper() + question[1:]
        if not question.endswith('?'):
            question += '?'
            
        # Сохраняет вопрос и ждем ответа
        session_data['current_question'] = question
        session_data['state'] = 'awaiting_answer'
        
        await update.message.reply_text(
            f"❓ Вопрос: {question}\n"
            "Какой ответ? (Да/Нет)",
            reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True)
        )

    @staticmethod
    async def _handle_answer(update, session_data: Dict[str, Any], answer: str):
        """Сохраняет ответ на вопрос в характеристиках персонажа"""
        question = session_data['current_question']
        character = session_data['character']
        
        # Преобразует ответ в True/False для удобства
        is_yes = answer.lower() in ['да', 'yes']
        character['traits'][question] = is_yes
        
        # Подтверждаем сохранение и предлагаем продолжить
        await update.message.reply_text(
            f"✅ Запомнил: {question} → {'Да' if is_yes else 'Нет'}\n\n"
            "Можешь добавить еще вопрос или написать \"Готово\"",
            reply_markup=ReplyKeyboardMarkup([['Готово']], one_time_keyboard=True)
        )

    @staticmethod
    async def _finish_learning(update, character_data: Dict[str, Any]):
        """Сохраняет нового персонажа в базу"""
        try:
            # Создает имя файла из имени персонажа
            filename = f"data/characters/{character_data['name'].lower().replace(' ', '_')}.json"
            
            # На всякий случай создает папку, если ее нет
            Path('data/characters').mkdir(exist_ok=True)
            
            # Сохраняет данные в JSON
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, ensure_ascii=False, indent=2)
                
            # Радует пользователя успешным завершением
            await update.message.reply_text(
                f"🎉 Персонаж '{character_data['name']}' успешно сохранен!\n"
                f"Всего характеристик: {len(character_data['traits'])}\n\n"
                "Теперь я смогу угадывать этого персонажа!",
                reply_markup=ReplyKeyboardRemove()
            )
            
        except Exception as e:
            # Если что-то пошло не так
            await update.message.reply_text(
                f"❌ Ой, что-то пошло не так: {str(e)}\n"
                "Давай попробуем еще раз позже",
                reply_markup=ReplyKeyboardRemove()
            )