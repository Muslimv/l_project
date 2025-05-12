from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.commands import start
from config import TOKEN
from engine.game import GameSession
from engine.learning import LearningMode



def main():
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", GameSession.start_game))
    app.add_handler(CommandHandler("learn", LearningMode.start_learning))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(
        filters.Regex("^(Да|Нет|Не знаю)$"), 
        GameSession.handle_answer
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        LearningMode.handle_learning
    ))
    
    app.run_polling()

if __name__ == "__main__":
    main()