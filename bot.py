import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# ================= НАСТРОЙКИ =================
# 1. Сюда вставь ТОКЕН бота Саши (получи у @BotFather)
BOT_TOKEN = '9179841512:AAGNFQAXE1b5VnhfrFt2Fkgd5jtBgew5RNQ'

# 2. Сюда вставь ID КАНАЛА Саши (начинается с -100...)
# Узнать можно через @getmyid_bot, переслав любой пост из канала.
CHANNEL_ID = -1001894502905 
# ============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- МАШИНА СОСТОЯНИЙ (Диалог с Саней) ---
class PostCreation(StatesGroup):
    waiting_for_photo = State()
    waiting_for_text = State()
    waiting_for_links = State()
    waiting_for_time = State()
    confirm_publish = State()

# --- КНОПКИ ---
def get_skip_keyboard(text="Пропустить"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="skip")]
    ])

def get_publish_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Опубликовать в канал", callback_data="publish")]
    ])

# --- ШАГ 1: СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Привет, Саня! Давай создадим анонс стрима.\n\nОтправь картинку для поста (или нажми кнопку ниже):", reply_markup=get_skip_keyboard("Без картинки"))
    await state.set_state(PostCreation.waiting_for_photo)

# --- ШАГ 2: КАРТИНКА ---
@dp.message(PostCreation.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Картинка сохранена! Теперь напиши текст для поста (или нажми 'Без текста'):", reply_markup=get_skip_keyboard("Без текста"))
    await state.set_state(PostCreation.waiting_for_text)

@dp.callback_query(PostCreation.waiting_for_photo, F.data == "skip")
async def skip_photo(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(photo=None)
    await callback.message.edit_text("Ок, без картинки. Теперь напиши текст для поста (или нажми 'Без текста'):", reply_markup=get_skip_keyboard("Без текста"))
    await state.set_state(PostCreation.waiting_for_text)

# --- ШАГ 3: ТЕКСТ ---
@dp.message(PostCreation.waiting_for_text, F.text)
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Текст записан! Теперь скинь ссылки на платформы ОДНИМ сообщением (каждую с новой строки), или нажми 'Пропустить':", reply_markup=get_skip_keyboard())
    await state.set_state(PostCreation.waiting_for_links)

@dp.callback_query(PostCreation.waiting_for_text, F.data == "skip")
async def skip_text(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(text=None)
    await callback.message.edit_text("Ок, без текста. Теперь скинь ссылки на платформы ОДНИМ сообщением (каждую с новой строки), или нажми 'Пропустить':", reply_markup=get_skip_keyboard())
    await state.set_state(PostCreation.waiting_for_links)

# --- ШАГ 4: ССЫЛКИ ---
@dp.message(PostCreation.waiting_for_links, F.text)
async def process_links(message: types.Message, state: FSMContext):
    await state.update_data(links=message.text)
    await message.answer("Ссылки приняты! Во сколько начало стрима? Напиши время (например, 20:00):")
    await state.set_state(PostCreation.waiting_for_time)

@dp.callback_query(PostCreation.waiting_for_links, F.data == "skip")
async def skip_links(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(links=None)
    await callback.message.edit_text("Ок, без ссылок. Во сколько начало стрима? Напиши время (например, 20:00):")
    await state.set_state(PostCreation.waiting_for_time)

# --- ШАГ 5: ВРЕМЯ И ПРЕДПРОСМОТР ---
@dp.message(PostCreation.waiting_for_time, F.text)
async def process_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    data = await state.get_data()
    
    # Формируем предпросмотр (тот самый кликабельный текст)
    preview_text = f"<b>{data.get('text', 'Анонс стрима')}</b>\n\n🕒 Начало: {data['time']}\n\n"
    
    if data.get('links'):
        # Делаем ссылки кликабельными (как ты и хотел)
        links_text = data['links']
        # Простая замена для красоты (можно расширить)
        links_text = links_text.replace("https://www.twitch.tv/", "<a href='https://www.twitch.tv/").replace("\n", "'>Twitch</a>\n")
        # Для простоты пока выведем как есть, но в следующем сообщении я покажу, как сделать красиво
        preview_text += f"Ссылки:\n{links_text}"
    
    if data.get('photo'):
        await message.answer_photo(photo=data['photo'], caption=preview_text, reply_markup=get_publish_keyboard(), parse_mode="HTML")
    else:
        await message.answer(preview_text, reply_markup=get_publish_keyboard(), parse_mode="HTML")
    
    await state.set_state(PostCreation.confirm_publish)

# --- ШАГ 6: ПУБЛИКАЦИЯ ---
@dp.callback_query(PostCreation.confirm_publish, F.data == "publish")
async def publish_post(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    # Собираем итоговый текст (здесь мы сделаем красивые ссылки)
    # В финальной версии мы сделаем парсинг строк, чтобы каждая ссылка стала словом-кнопкой
    text = f"<b>{data.get('text', 'Анонс стрима')}</b>\n\n🕒 Начало: {data['time']}\n\n"
    
    buttons = []
    if data.get('links'):
        # Разбиваем ссылки по строкам и создаем кнопки (пока так, для теста)
        lines = data['links'].split('\n')
        for line in lines:
            if "twitch" in line:
                buttons.append([InlineKeyboardButton(text="Twitch 🟣", url=line.strip())])
            elif "youtube" in line:
                buttons.append([InlineKeyboardButton(text="YouTube ▶️", url=line.strip())])
            elif "vkvideo" in line:
                buttons.append([InlineKeyboardButton(text="VK Play 🎮", url=line.strip())])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    try:
        if data.get('photo'):
            await bot.send_photo(chat_id=CHANNEL_ID, photo=data['photo'], caption=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=text, reply_markup=keyboard, parse_mode="HTML")
        
        await callback.message.edit_text("✅ Пост успешно опубликован в канале!")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка публикации: {e}. Проверь, что бот админ в канале.")
    
    await state.clear()

# --- ЗАПУСК ---
async def main():
    print("🚀 Бот-автопостер запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())