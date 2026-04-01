import asyncio
from aiogram import F, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
import logging
from handlers import cmd_start, start_order_process, handle_photo_step, process_cancel, process_confirm, export_to_excel_handler, clear_cart_handler
from states import OrderStates
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')

if not bot_token:
    logging.critical("❌ ОШИБКА: Ключ OP_API_KEY или BOT_TOKEN не найден в .env файле!")

bot = Bot(token=bot_token)
dp = Dispatcher()

dp.message.register(cmd_start, Command('start'))
dp.message.register(start_order_process, F.text == '🚀 Начать заказ')
dp.callback_query.register(start_order_process, F.data == 'start_order_process')
dp.message.register(handle_photo_step, OrderStates.waiting_for_scan, F.photo)
dp.callback_query.register(process_confirm, F.data == 'confirm_items')
dp.callback_query.register(process_cancel, F.data == 'cancel_items')
dp.callback_query.register(export_to_excel_handler, F.data == "generate_excel")
dp.callback_query.register(clear_cart_handler, F.data == "clear_cart")

async def main():
    await dp.start_polling(bot)
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())