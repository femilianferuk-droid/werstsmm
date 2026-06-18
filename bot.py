import asyncio
import logging
import os
import requests
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Конфигурация
API_KEY = "2af40926afe4cc8ab20ae1eb7839e428f396c1a0852888b4e420c4315a8fdfd0"
API_BASE_URL = "https://vestsmm.shop/api/v1"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище заказов в памяти
orders_storage = []

# Состояния для FSM
class OrderStates(StatesGroup):
    waiting_for_service = State()
    waiting_for_link = State()
    waiting_for_quantity = State()

# Функции для работы с API
def get_services():
    """Получить список услуг"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/services",
            params={"api_key": API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logging.error(f"Error fetching services: {e}")
        return []

def create_order_api(service_id, link, quantity):
    """Создать заказ через API"""
    try:
        payload = {
            "api_key": API_KEY,
            "service_id": service_id,
            "link": link,
            "quantity": quantity
        }
        response = requests.post(
            f"{API_BASE_URL}/order",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logging.error(f"Error creating order: {e}")
        return None

def check_order_status(order_id):
    """Проверить статус заказа"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/order/status",
            params={"api_key": API_KEY, "order_id": order_id},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logging.error(f"Error checking order status: {e}")
        return None

# Клавиатуры
def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список услуг", callback_data="services")],
        [InlineKeyboardButton(text="🛒 Создать заказ", callback_data="new_order")],
        [InlineKeyboardButton(text="📊 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔄 Обновить статусы", callback_data="update_statuses")]
    ])
    return keyboard

def get_services_keyboard(services, page=0, per_page=10):
    """Клавиатура со списком услуг"""
    start = page * per_page
    end = start + per_page
    services_page = services[start:end]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"ID:{s['service_id']} - {s['name'][:30]} ({s['rate']}₽)",
            callback_data=f"order_service_{s['service_id']}"
        )] for s in services_page
    ])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"services_page_{page-1}"))
    if end < len(services):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"services_page_{page+1}"))
    
    if nav_buttons:
        keyboard.inline_keyboard.append(nav_buttons)
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    
    return keyboard

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 <b>Добро пожаловать в Werts Smm Bot!</b>\n\n"
        "🚀 Профессиональная накрутка подписчиков, лайков и просмотров в социальных сетях.\n\n"
        "📋 <b>Доступные действия:</b>\n"
        "• Просмотр списка услуг\n"
        "• Создание заказа на накрутку\n"
        "• Отслеживание статуса заказов\n"
        "• Автоматическое обновление статусов\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "🤖 <b>Помощь по боту Werts Smm</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/services - Список услуг\n"
        "/order - Создать заказ\n"
        "/orders - Мои заказы\n"
        "/update - Обновить статусы\n"
        "/help - Помощь\n\n"
        "<b>Как создать заказ:</b>\n"
        "1. Выберите услугу из списка\n"
        "2. Укажите ссылку\n"
        "3. Укажите количество\n"
        "4. Подтвердите заказ"
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("services"))
async def cmd_services(message: types.Message):
    """Показать список услуг"""
    services = get_services()
    if services:
        await message.answer(
            "📋 <b>Список доступных услуг:</b>",
            reply_markup=get_services_keyboard(services),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Не удалось загрузить список услуг")

@dp.message(Command("orders"))
async def cmd_orders(message: types.Message):
    """Показать заказы пользователя"""
    user_orders = [o for o in orders_storage if o.get('user_id') == message.from_user.id]
    
    if not user_orders:
        await message.answer("📊 У вас пока нет заказов")
        return
    
    orders_text = "📊 <b>Ваши заказы:</b>\n\n"
    for order in user_orders[-10:]:  # Последние 10 заказов
        status_emoji = {
            'pending': '⏳',
            'processing': '🔄',
            'in_progress': '🔄',
            'completed': '✅',
            'partial': '⚠️',
            'canceled': '❌'
        }.get(order['status'], '❓')
        
        orders_text += (
            f"{status_emoji} <b>Заказ #{order['order_id']}</b>\n"
            f"📌 Услуга: {order['service_name']}\n"
            f"🔗 Ссылка: {order['link'][:30]}...\n"
            f"📊 Количество: {order['quantity']}\n"
            f"💰 Сумма: {order['charge']} руб.\n"
            f"📅 Дата: {order['created_at']}\n"
            f"Статус: {order['status']}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статусы", callback_data="update_statuses")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(orders_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message(Command("update"))
async def cmd_update(message: types.Message):
    """Обновить статусы заказов"""
    updated = 0
    for order in orders_storage:
        if order['status'] not in ['completed', 'canceled']:
            status_data = check_order_status(order['order_id'])
            if status_data:
                order['status'] = status_data.get('status', order['status'])
                updated += 1
    
    await message.answer(f"🔄 Обновлено заказов: {updated}")

# Обработчики callback_query
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "👋 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "services")
async def callback_services(callback: types.CallbackQuery):
    """Показать список услуг"""
    services = get_services()
    if services:
        await callback.message.edit_text(
            "📋 <b>Список доступных услуг:</b>",
            reply_markup=get_services_keyboard(services),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Не удалось загрузить услуги", show_alert=True)

@dp.callback_query(F.data.startswith("services_page_"))
async def callback_services_page(callback: types.CallbackQuery):
    """Пагинация услуг"""
    page = int(callback.data.split("_")[2])
    services = get_services()
    if services:
        await callback.message.edit_reply_markup(
            reply_markup=get_services_keyboard(services, page)
        )

@dp.callback_query(F.data == "new_order")
async def callback_new_order(callback: types.CallbackQuery, state: FSMContext):
    """Начать создание заказа"""
    services = get_services()
    if services:
        await callback.message.edit_text(
            "📋 <b>Выберите услугу:</b>",
            reply_markup=get_services_keyboard(services),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Не удалось загрузить услуги", show_alert=True)

@dp.callback_query(F.data.startswith("order_service_"))
async def callback_order_service(callback: types.CallbackQuery, state: FSMContext):
    """Выбор услуги для заказа"""
    service_id = int(callback.data.split("_")[2])
    await state.update_data(service_id=service_id)
    await state.set_state(OrderStates.waiting_for_link)
    
    await callback.message.edit_text(
        f"🔗 <b>Укажите ссылку для накрутки:</b>\n\n"
        f"Например: https://t.me/your_channel",
        parse_mode="HTML"
    )

@dp.message(OrderStates.waiting_for_link)
async def process_link(message: types.Message, state: FSMContext):
    """Обработка ссылки"""
    await state.update_data(link=message.text)
    await state.set_state(OrderStates.waiting_for_quantity)
    
    await message.answer(
        "📊 <b>Укажите количество:</b>\n\n"
        "Введите число (например: 1000)",
        parse_mode="HTML"
    )

@dp.message(OrderStates.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    """Обработка количества и создание заказа"""
    try:
        quantity = int(message.text)
        data = await state.get_data()
        service_id = data['service_id']
        link = data['link']
        
        # Создаем заказ через API
        result = create_order_api(service_id, link, quantity)
        
        if result and result.get('success'):
            # Сохраняем заказ
            order = {
                'order_id': result['order_id'],
                'user_id': message.from_user.id,
                'service_id': result['service_id'],
                'service_name': f"Service {result['service_id']}",
                'link': result['link'],
                'quantity': result['quantity'],
                'charge': result['charge'],
                'status': 'pending',
                'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
            orders_storage.append(order)
            
            await message.answer(
                f"✅ <b>Заказ успешно создан!</b>\n\n"
                f"📋 ID заказа: {result['order_id']}\n"
                f"📌 Услуга ID: {result['service_id']}\n"
                f"🔗 Ссылка: {result['link']}\n"
                f"📊 Количество: {result['quantity']}\n"
                f"💰 Сумма: {result['charge']} руб.\n\n"
                f"Используйте /orders для просмотра статуса",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ <b>Ошибка при создании заказа</b>\n\n"
                "Попробуйте позже или выберите другую услугу",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    finally:
        await state.clear()

@dp.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: types.CallbackQuery):
    """Показать мои заказы"""
    user_orders = [o for o in orders_storage if o.get('user_id') == callback.from_user.id]
    
    if not user_orders:
        await callback.message.edit_text(
            "📊 У вас пока нет заказов",
            reply_markup=get_main_keyboard()
        )
        return
    
    orders_text = "📊 <b>Ваши заказы:</b>\n\n"
    for order in user_orders[-10:]:
        status_emoji = {
            'pending': '⏳',
            'processing': '🔄',
            'in_progress': '🔄',
            'completed': '✅',
            'partial': '⚠️',
            'canceled': '❌'
        }.get(order['status'], '❓')
        
        orders_text += (
            f"{status_emoji} <b>Заказ #{order['order_id']}</b>\n"
            f"📌 Услуга: {order['service_name']}\n"
            f"🔗 {order['link'][:30]}...\n"
            f"📊 {order['quantity']} | 💰 {order['charge']}₽\n"
            f"📅 {order['created_at']}\n"
            f"Статус: {order['status']}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статусы", callback_data="update_statuses")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(orders_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "update_statuses")
async def callback_update_statuses(callback: types.CallbackQuery):
    """Обновить статусы заказов"""
    updated = 0
    for order in orders_storage:
        if order['status'] not in ['completed', 'canceled']:
            status_data = check_order_status(order['order_id'])
            if status_data:
                order['status'] = status_data.get('status', order['status'])
                updated += 1
    
    await callback.answer(f"✅ Обновлено заказов: {updated}", show_alert=True)
    await callback_my_orders(callback)

# Обработчик для неизвестных команд
@dp.message()
async def unknown_command(message: types.Message):
    """Обработчик неизвестных команд"""
    await message.answer(
        "🤔 Неизвестная команда. Используйте /help для списка команд",
        reply_markup=get_main_keyboard()
    )

# Запуск бота
async def main():
    """Запуск бота"""
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found in environment variables")
    
    asyncio.run(main())
