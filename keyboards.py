from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

submit_btn = InlineKeyboardButton(text='Подтвердить', callback_data='main_menu')
restart_registration = InlineKeyboardButton(text='Ввести данные заново', callback_data='start_registration')
user_reg_kb = InlineKeyboardBuilder()
user_reg_kb.add(submit_btn).add(restart_registration)

make_order_btn = InlineKeyboardButton(text='Сделать заказ', callback_data='new_request')
my_orders_btn = InlineKeyboardButton(text='Мои заказы', callback_data='my_requests')
main_menu_kb = InlineKeyboardBuilder()
main_menu_kb.add(make_order_btn).add(my_orders_btn)


check_requests = InlineKeyboardButton(text='Посмотреть заявки', callback_data='check')
