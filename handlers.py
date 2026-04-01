from aiogram import F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import OrderStates
from ai_client import AIClient
import logging
from database import Database
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import os
from dotenv import load_dotenv
from excel_generator import create_excel
from typing import Union


load_dotenv()
api_key = os.getenv('OP_API_KEY')
logger = logging.getLogger(__name__)


async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    kb = [
        [KeyboardButton(text='🚀 Начать заказ')]
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb, resize_keyboard=True
    )
    
    await message.answer(
        f'Привет, {message.from_user.first_name}! Я помогу тебе собрать заказ для Честного Знака.\n'
        'Нажми на кнопку, чтобы прислать товар.',
        reply_markup=keyboard
    )
    
async def start_order_process(event: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()
    if isinstance(event, Message):
        await event.answer(
        "Пришлите **фото товара одним сообщением вместе с описанием**.\n\n"
        "В описании укажите: Артикул, Бренд, Состав, Цвета и количество.\n"
        "Пожалуйста, отправляйте красивую и аккуратную информацию, чтобы я смог разобраться в ней",
        reply_markup=ReplyKeyboardRemove()
        )
    elif isinstance(event, CallbackQuery):
        await event.answer() 
        await event.message.answer("Пришлите следующее описание и фото товара 📸")
        
    await state.set_state(OrderStates.waiting_for_scan)

async def handle_photo_step(message: Message, state: FSMContext):
    if not message.caption:
        await message.answer("⚠️ Вы забыли прислать описание! Пожалуйста, пришлите фото СРАЗУ с текстом.")
        return
    
    photo_id = message.photo[-1].file_id
    description = message.caption
    
    await state.update_data(photo_id=photo_id, desc=description)
    
    await message.answer(f"✅ Фото и описание получены!\n\nТекст: {description[:50]}...")
    await message.answer("⏳ Начинаю обработку через ИИ...")
    from main import bot
    
    file = await message.bot.get_file(photo_id)
    file_bytes = await message.bot.download_file(file.file_path)
    
    image_data = file_bytes.read()
    
    result = await AIClient.get_product_data(image_data, description, api_key)
    
    print(result)
    
    if isinstance(result, list):
        products = result
    elif isinstance(result, dict):
        products = result.get('products', [])
    else:
        products = []
    
    all_rows = []
    
    for product in products:
        brand = product.get("brand", "Без бренда")
        article = product.get("article", "Не указан")
        p_type = product.get("type", "Товар")
        color = product.get("color", "—")
        gender = product.get('gender', "Унисекс")
        compound = product.get("compound", "—")
        
        for s in product.get('sizes', []):
            row = {
                'brand': brand,
                'article': article,
                'type': p_type,
                'color': color,
                'gender': gender,
                'compound': compound,
                'size': s.get('value', '-'),
                'count': s.get('count', 1) 
            }
            all_rows.append(row)
    
    await state.update_data(temp_items=all_rows)
    
    # Формируем красивую сводку
    summary = "📦 **НОВАЯ ПОЗИЦИЯ В ЗАКАЗ**\n"
    summary += "—" * 20 + "\n\n"

    # Проходим по всем строкам урожая
    for i, row in enumerate(all_rows, 1):
        summary += f"*{i}. {row['type'].upper()}*\n"
        summary += f"🏷 **Бренд:** {row['brand']}\n"
        summary += f"🎨 **Цвет:** {row['color']}\n"
        summary += f"🧬 **Состав:** {row['compound']}\n"
        summary += f"👤 **Пол:** {row['gender']}\n"
        summary += f"🔢 **Арт:** `{row['article']}`\n"
        summary += f"📏 **Размер:** `{row['size']}` — **{row['count']} шт.**\n"
        summary += "—" * 15 + "\n"

    summary += "\n✨ **Всё верно?** Нажмите кнопку ниже, чтобы добавить в корзину."
        
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_items"),
            InlineKeyboardButton(text="❌ Удалить", callback_data="cancel_items")
        ]
    ])
        
    await message.answer(summary, reply_markup=ikb, parse_mode='Markdown')

async def process_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    # Забираем данные и СРАЗУ удаляем их из словаря, чтобы второй клик их не нашел
    items = data.pop('temp_items', None) 
    
    if not items:
        await callback.answer("⚠️ Эти данные уже добавлены", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    # Обновляем стейт уже БЕЗ этих данных, но сохраняем другие (если есть)
    await state.set_data(data) 
    
    db = Database()
    db.save_cart(callback.from_user.id, items) # Теперь в БД пойдет только один раз
    
    full_cart = db.get_cart(callback.from_user.id)
    total_items = len(full_cart)
    total_qty = sum(int(i['count']) for i in full_cart)
    
    text = (
        f"✅ **Товар добавлен!**\n\n"
        f"📊 **Сейчас в корзине:**\n"
        f"• Позиций: {total_items}\n"
        f"• Всего штук: {total_qty}\n\n"
        f"Присылайте следующее фото или сформируйте Excel."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить еще", callback_data="start_order_process")],
        [InlineKeyboardButton(text="📥 Сформировать Excel", callback_data="generate_excel")],
        [InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_cart")]
    ])
    
    # Редактируем сообщение (убираем старую сводку и кнопки Подтвердить/Отменить)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='Markdown')
    await callback.answer()

async def process_cancel(callback: CallbackQuery, state: FSMContext):
    # 1. Очищаем старые временные данные, чтобы не было путаницы
    await state.clear()
    
    # 2. Устанавливаем стейт ожидания НОВОГО фото (или исправленного текста)
    await state.set_state(OrderStates.waiting_for_scan)
    
    # 3. Редактируем сообщение, чтобы юзер видел: "Я готов, шли заново"
    text = (
        "❌ **Запись отменена.**\n\n"
        "Пожалуйста, исправьте описание и **пришлите фото вместе с текстом заново**. "
        "Я постараюсь распознать точнее! 🫡"
    )
    
    try:
        await callback.message.edit_text(text, parse_mode='Markdown')
    except Exception:
        # На случай, если это было сообщение с фото (caption)
        await callback.message.edit_caption(caption=text, parse_mode='Markdown')
        
    await callback.answer("Готов к новой попытке")
    
async def export_to_excel_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    db = Database()
    items = db.get_cart(user_id)
    
    if not items:
        await callback.answer("❌ Корзина пуста. Нечего выгружать!", show_alert=True)
        return

    await callback.message.answer("⏳ Генерирую актуальную версию файла...")

    try:
        # Генерируем файл
        file_path = create_excel(user_id, items)
        
        # Подготавливаем файл для отправки
        excel_file = FSInputFile(file_path)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Продолжить заполнение", callback_data="start_order_process")],
        [InlineKeyboardButton(text="🧹 Начать новый заказ (очистить)", callback_data="clear_cart")]
        ])
        
        await callback.message.answer_document(
            document=excel_file,
            caption=f"📊 Промежуточный отчет\nПозиций в базе: {len(items)}\n\nПроверьте файл. Если всё ок, можно продолжить!",
            reply_markup=kb
        )
        
        await callback.answer()

    except Exception as e:
        print(f"Ошибка при создании Excel: {e}")
        await callback.message.answer("❌ Произошла ошибка при формировании файла. Проверьте консоль.")

    await callback.answer()

async def clear_cart_handler(callback: CallbackQuery):
    db = Database()
    db.clear_cart(callback.from_user.id) 
    
    text = '🗑 **Корзина очищена.**\nПришлите новое фото или нажмите кнопку в меню.'
    
    # Создаем инлайн-кнопку, так как мы РЕДАКТИРУЕМ сообщение
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать новый заказ", callback_data="start_order_process")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode='Markdown')
    except Exception:
        # Если было фото, пытаемся отредактировать подпись
        try:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode='Markdown')
        except Exception:
            # Если совсем всё плохо — просто шлем новое сообщение
            await callback.message.answer(text, reply_markup=kb)
            
    await callback.answer("Корзина пуста")
    
