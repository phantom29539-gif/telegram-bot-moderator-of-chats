import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import register_handlers

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
# В новой версии Aiogram 3.7+ нужно использовать DefaultBotProperties
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


async def main():
    """Главная функция запуска бота"""

    # Регистрируем все обработчики
    await register_handlers(dp)

    # Удаляем вебхук (если был), чтобы переключиться на polling
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем поллинг
    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())