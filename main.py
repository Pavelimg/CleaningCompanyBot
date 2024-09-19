import asyncio
import datetime
from time import gmtime, strftime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup

from DBControl import DataBase
from config import *
from keyboards import *

dp = Dispatcher()
telegram_bot = Bot(token=tg_token)
db = DataBase(db_path)  # Подключаем базу данных

user_cart = {}
user_comments = {}
admins_time = {}


@dp.message(Command("admin"))
async def start_message(message: types.Message):
    sender_id = message.from_user.id
    if sender_id not in admins:
        await telegram_bot.send_message(text="Вы не администратор")
        return
    await telegram_bot.send_message(chat_id=sender_id, text="Меню администратора",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text="Перейти", callback_data=f'check_free_request')]]))


@dp.message(Command("worker"))
async def start_message(message: types.Message):
    sender_id = message.from_user.id
    if sender_id not in list(map(lambda x: x[1], db.get_teams())):
        await telegram_bot.send_message(sender_id, text="Вы не являетесь работником")
        return

    await telegram_bot.send_message(sender_id, text="Меню бригады:",
                                    reply_markup=InlineKeyboardMarkup(
                                        inline_keyboard=[[InlineKeyboardButton(text=f'Посмотреть заявки',
                                                                               callback_data=f'check_request')]]))


@dp.message(Command("start"))
async def start_message(message: types.Message):
    sender_id = message.from_user.id
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Зарегистрироваться", callback_data="start_registration"))
    await telegram_bot.send_message(chat_id=sender_id, text="Здравствуйте! Что бы зарегистрироваться нажмите кнопку",
                                    reply_markup=builder.as_markup())


@dp.callback_query(lambda c: c.data == "start_registration")
async def start_registration(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    if db.check_user_registration(sender_id):
        db.delete_user(sender_id)
    await telegram_bot.send_message(chat_id=sender_id, text="Для продолжения введите ФИО в формате\n"
                                                            "'Фамилия Имя Отчество' или \n'Фамилия Имя'")


@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(message: types.Message):
    sender_id = message.from_user.id
    if sender_id in user_cart.keys():
        user_cart.pop(sender_id)
    if db.check_user_data(sender_id):
        return await telegram_bot.send_message(chat_id=sender_id, text="Выберите действие",
                                               reply_markup=main_menu_kb.as_markup())
    else:
        await start_message(message)


@dp.callback_query(lambda c: c.data == "my_requests")
async def my_requests(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    requests = db.get_user_requests(sender_id)
    if len(requests) == 0:
        await telegram_bot.send_message(chat_id=sender_id, text="У вас нет заказов",
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text="В меню", callback_data=f'main_menu')]]))
    else:
        buttons = []
        for i in requests:
            if i[1] == "":
                buttons.append([InlineKeyboardButton(text=f"Заказ №{i[0]}", callback_data=f'get_request {i[0]}')])
            else:
                buttons.append([InlineKeyboardButton(text=f"{i[0]}:{i[1]}", callback_data=f'get_request {i[0]}')])
        buttons.append([InlineKeyboardButton(text="В меню", callback_data=f'main_menu')])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await telegram_bot.send_message(chat_id=sender_id, text="Выберете заказ:", reply_markup=kb)


@dp.callback_query(lambda c: c.data.startswith("get_request"))
async def my_requests(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    request_id = callback.data.split()[1]
    request = db.get_request(request_id)
    text = f"Заявка №{request_id}\n"
    if request['team']:
        text += f"Вам назначена бригада №{request['team']}\n"
    else:
        text += "Бригада ещё не назначена\n"

    if request['time']:
        text += f"Бригада приедет в {strftime('%H:%M %m.%d.%Y', gmtime(request['time'] + 3600 * timezone))}\n"
    else:
        text += "Время ещё не назначено\n"
    if request['details'] != "":
        text += f"Ваш комментарий: {request['details']}\n"
    text += f"Список услуг:\n\n"

    price = 0
    for i, value in enumerate(request['service']):
        if value[2] != "":
            text += f"№{i + 1} {value[0]}\nСтоимость:{value[1]}\nОписание:{value[2]}\n\n"
        else:
            text += f"№{i + 1} {value[0]}\nСтоимость:{value[1]}\n\n"
        price += value[1]
    text += f"Итоговая стоимость:{price}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data=f'my_requests')]])
    await telegram_bot.send_message(chat_id=sender_id, text=text, reply_markup=kb)


@dp.callback_query(lambda c: c.data == "new_request")
async def new_request(callback: types.CallbackQuery):
    sender_id = callback.from_user.id

    text = ""
    buttons = []
    for i in db.get_price_list():
        if not i[3] == "":
            text += f'{i[1]}\nСтоимость: {i[2]} рублей\nОписание: {i[3]}\n\n'
        else:
            text += f'{i[1]}\nСтоимость: {i[2]} рублей\n\n'
        btn = InlineKeyboardButton(text=i[1], callback_data=f'add_service {i[0]}')
        buttons.append([btn])
    buttons.append([InlineKeyboardButton(text="В меню", callback_data=f'main_menu')])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await telegram_bot.send_message(chat_id=sender_id, text=text, reply_markup=kb)


@dp.callback_query(lambda c: c.data.startswith("add_service") or c.data.startswith("remove_service"))
async def add_or_remove_service(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    service_id = int(callback.data.split(" ")[1])
    if sender_id not in user_cart:
        user_cart[sender_id] = []
    if service_id != -1:
        if "add" in callback.data:
            if sender_id not in user_cart.keys():
                user_cart[sender_id] = [service_id]
            else:
                user_cart[sender_id].append(service_id)
        else:
            if sender_id in user_cart.keys() and service_id in user_cart[sender_id]:
                user_cart[sender_id].remove(service_id)

    text = ""
    buttons = []
    for i in db.get_price_list():
        if not i[3] == "":
            text += f'{i[1]}\nСтоимость: {i[2]} рублей\nОписание: {i[3]}\n'
        else:
            text += f'{i[1]}\nСтоимость: {i[2]} рублей\n'
        if i[0] in user_cart[sender_id]:
            text += "(Добавлено)\n\n"
            btn = InlineKeyboardButton(text=f"{i[1]} (Убрать)", callback_data=f'remove_service {i[0]}')
        else:
            text += "\n"
            btn = InlineKeyboardButton(text=i[1], callback_data=f'add_service {i[0]}')
        buttons.append([btn])
    if user_cart[sender_id]:
        buttons.append([InlineKeyboardButton(text="Подтвердить", callback_data=f'form_request'),
                        InlineKeyboardButton(text="В меню", callback_data=f'main_menu')])
    else:
        buttons.append([InlineKeyboardButton(text="В меню", callback_data=f'main_menu')])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await telegram_bot.send_message(chat_id=sender_id, text=text, reply_markup=kb)


@dp.callback_query(lambda c: c.data == "form_request")
async def add_or_remove_service(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    price = 0
    for i in db.get_price_list():
        if i[0] in user_cart[sender_id]:
            price += i[2]
    buttons = [[InlineKeyboardButton(text="Сформировать заказ", callback_data=f'create_request'),
                InlineKeyboardButton(text="Назад", callback_data=f'add_service -1')]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await telegram_bot.send_message(chat_id=sender_id, text=f"Сумма вашего заказа:{price}\nЕсли вы хотите добавить"
                                                            f" комментарий к заказу, то отправьте его сюда или "
                                                            f"перейдите в главное меню", reply_markup=kb)


@dp.callback_query(lambda c: c.data == "create_request")
async def add_or_remove_service(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    if sender_id not in user_comments:
        db.new_request(sender_id, user_cart[sender_id])
    else:
        db.new_request(sender_id, user_cart[sender_id], user_comments[sender_id])
        user_comments.pop(sender_id)
        user_cart.pop(sender_id)

    await telegram_bot.send_message(chat_id=sender_id, text="Заявка отправлена",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                        [InlineKeyboardButton(text="В меню", callback_data=f'main_menu')]]))
    for i in admins:
        await telegram_bot.send_message(chat_id=i, text="Поступила новая заявка")


@dp.callback_query(lambda c: c.data.startswith("check_free_request"))
async def check_free_request(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    if sender_id not in admins:
        return

    requests = db.get_free_requests()
    if len(requests) == 0:
        await telegram_bot.send_message(chat_id=sender_id, text="Заявок нет",
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                            [InlineKeyboardButton(text="Проверить заявки",
                                                                  callback_data=f'check_free_request')]]))
        return
    text = f"{len(requests)} неразобранных заявок\n\n"
    buttons = []
    for value in requests:
        if value['user']['Patronymic'] is None:
            patronymic = ""
        else:
            patronymic = value['user']['Patronymic']
        if value['Details'] == "":
            details = ""
        else:
            details = f"Комментарий заказчика: {value['Details']}\n"

        text += f"Заявка №{value['request_id']}\n" \
                f"ФИО: {value['user']['FirstName']} {value['user']['Surname']} {patronymic}\n" \
                f"Адрес: {value['Address']}\n" \
                f"{details}\n"
        buttons.append([InlineKeyboardButton(text=f'Назначить бригаду для №{value["request_id"]}',
                                             callback_data=f'select_team_to_request {value["request_id"]}')])
    await telegram_bot.send_message(chat_id=sender_id, text=text,
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(lambda c: c.data.startswith("select_team_to_request"))
async def check_free_request(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    request_id = callback.data.split()[1]
    if sender_id not in admins:
        return
    buttons = []
    text = "Введите время в формате 'мм:чч ДД.ММ' и нажмите на название бригады, которую хотите назначить:\n\n"
    for value in db.get_teams():
        text += f'Бригада №{str(value[0])}\nTelegram id:{str(value[1])}\n\n'
        buttons.append([InlineKeyboardButton(text=f'Бригада №{str(value[0])}',
                                             callback_data=f'set_team_to_request {str(value[1])} {str(request_id)}')])
    await telegram_bot.send_message(chat_id=sender_id, text=text,
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(lambda c: c.data.startswith("set_team_to_request"))
async def check_free_request(callback: types.CallbackQuery):
    _, team_tg, request_id, = callback.data.split()
    sender_id = callback.from_user.id
    if sender_id not in admins_time:
        await telegram_bot.send_message(sender_id, text="Вы не ввели время")
        return
    db.set_team_to_request(team_tg, request_id, admins_time[sender_id])
    await telegram_bot.send_message(chat_id=sender_id,
                                    text=f"Бригада назначена на заявку {request_id} на время"
                                         f" {strftime('%H:%M %m.%d.%Y', gmtime(admins_time[sender_id] + 3600 * timezone))}",
                                    reply_markup=InlineKeyboardMarkup(
                                        inline_keyboard=[[InlineKeyboardButton(
                                            text=f'Продолжить',
                                            callback_data=f'check_free_request')]]))
    await telegram_bot.send_message(chat_id=db.get_user_by_request(request_id),
                                    text=f"Статус заявки №{request_id} изменился")
    admins_time.pop(sender_id)


@dp.callback_query(lambda c: c.data.startswith("worker_menu"))
async def check_free_request(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    if sender_id not in list(map(lambda x: x[1], db.get_teams())):
        await telegram_bot.send_message(sender_id, text="Вы не являетесь работником")
        return

    await telegram_bot.send_message(sender_id, text="Меню бригады:",
                                    reply_markup=InlineKeyboardMarkup(
                                        inline_keyboard=[[InlineKeyboardButton(text=f'Посмотреть заявки',
                                                                               callback_data=f'check_request')]]))


@dp.callback_query(lambda c: c.data.startswith("check_request"))
async def check_free_request(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    res = db.get_team_requests(sender_id)
    if len(res) == 0:
        await telegram_bot.send_message(sender_id, text="Заявок нет!",
                                        reply_markup=InlineKeyboardMarkup(
                                            inline_keyboard=[[InlineKeyboardButton(text=f'Посмотреть заявки',
                                                                                   callback_data=f'check_request')]]))
        return
    buttons = []
    text = f"У вас {len(res)} заявок\n" \
           f"Нажмите что бы отметить как выполнено\n\n"
    for value in db.get_team_requests(sender_id):
        text += f'Заявка №{str(value["request_id"])}\n' \
                f"Время:{strftime('%H:%M %m.%d.%Y', gmtime(value['time'] + 3600 * timezone))}\n" \
                f"Адрес: {value['Address']}" \
                f"Комментарий: {value['Details']}\n\n"
        buttons.append([InlineKeyboardButton(text=f'Заявка №{value["request_id"]}',
                                             callback_data=f'set_request_complete {value["request_id"]}')])
    buttons.append([InlineKeyboardButton(text=f'Обновить заявки',
                                         callback_data=f'check_request')])
    await telegram_bot.send_message(chat_id=sender_id, text=text,
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(lambda c: c.data.startswith("set_request_complete"))
async def check_free_request(callback: types.CallbackQuery):
    sender_id = callback.from_user.id
    request_id = callback.data.split()[1]
    for_user_id = db.get_user_by_request(request_id=request_id)
    db.set_request_complete(request_id)
    await telegram_bot.send_message(chat_id=sender_id, text=f"Заявка №{request_id} отмечена, как выполненная")
    for i in admins:
        await telegram_bot.send_message(chat_id=i,
                                        text=f"Статус заявки Статус заявки №{request_id} изменён на 'выполнено'")
    await telegram_bot.send_message(chat_id=for_user_id,
                                    text=f"Ваша заявка №{request_id} выполнена!")


@dp.message()
async def new_message(message: types.Message):
    sender_id = message.from_user.id

    if sender_id in admins:
        user_role = "admin"
    else:
        user_role = "user"
    registration = db.check_user_registration(sender_id)
    has_address = db.check_user_address(sender_id)

    if user_role == "admin":
        try:
            req_time = datetime.datetime.strptime(message.text + "." + str(datetime.datetime.now().year),
                                                  '%H:%M %m.%d.%Y')
            admins_time[sender_id] = int(req_time.timestamp())
        except Exception:
            await telegram_bot.send_message(chat_id=sender_id, text="Неверный формат даты")
    if user_role == "worker":
        await telegram_bot.send_message(chat_id=sender_id, text="Здравствуйте!",
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text=f'Открыть меню',
                                                                 callback_data=f'worker_menu')
                                        ]]))
    elif user_role == "user" and not registration:
        spited = message.text.split()
        if 3 >= len(spited) >= 2:
            surname, firstname, *patronymic = spited
        else:
            return
        print()
        if not patronymic:
            db.new_user(user_tg=sender_id, first_name=firstname, surname=surname)
        else:
            db.new_user(user_tg=sender_id, first_name=firstname, surname=surname, patronymic=patronymic[0])
        await telegram_bot.send_message(chat_id=sender_id, text="Введите ваш адрес")
    elif user_role == "user" and not has_address:
        db.add_user_info(sender_id, address=message.text)
        user_info = db.get_user_info(sender_id)
        await telegram_bot.send_message(chat_id=sender_id, text="Проверьте ваши данные\n"
                                                                f"Фамилия: {user_info['user']['Surname']}\n"
                                                                f"Имя: {user_info['user']['FirstName']}\n"
                                                                f"Отчество: {user_info['user']['Patronymic']}\n"
                                                                f"Адре0с: {user_info['Address']}\n",
                                        reply_markup=user_reg_kb.as_markup())
    elif sender_id in user_cart:
        user_comments[sender_id] = message.text
        await telegram_bot.send_message(sender_id, "Комментарий к вашему заказу добавлен")


async def polling():
    await dp.start_polling(telegram_bot)
    print("Started")


asyncio.run(polling())
