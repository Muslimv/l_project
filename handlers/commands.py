from telegram import ReplyKeyboardMarkup

async def start(update, context):
    """Обработчик команды /start"""
    welcome_text = (
        "🎮 Добро пожаловать в Акинатор-бота!\n"
        "Я могу угадать любого персонажа по вашим ответам.\n\n"
        "Доступные команды:\n"
        "/play - Начать игру\n"
        "/learn - Научить меня новому персонажу\n"
        "/stats - Ваша статистика"
    )
    await update.message.reply_text(welcome_text)

async def stats(update, context):
    """Показывает статистику игрока"""
    await update.message.reply_text("Статистика в разработкe...")