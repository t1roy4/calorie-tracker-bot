import re
import telebot
from telebot import types

from foods import find_food, FOODS
from database import (
    init_db, add_entry, get_today_summary,
    set_goal, get_goal, add_custom_food, find_custom_food,
)
from ai import ask_ai_for_food

# ВАЖНО: вставь сюда свой токен от @BotFather
TOKEN = ""

bot = telebot.TeleBot(TOKEN)
init_db()

BTN_TODAY = "📊 Сегодня"
BTN_ADDFOOD = "➕ Добавить продукт"
BTN_GOAL = "🎯 Задать норму"
BTN_FOODS = "📋 Список продуктов"


def main_menu():
    """Главное меню — кнопки внизу экрана вместо ввода команд руками."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(BTN_TODAY, BTN_ADDFOOD, BTN_GOAL, BTN_FOODS)
    return markup


def parse_grams_and_name(text: str):
    """Достаёт число (граммы) и название продукта из текста вида 'гречка 150'."""
    match = re.search(r"(\d+[.,]?\d*)", text)
    if not match:
        return None, None
    grams = float(match.group(1).replace(",", "."))
    name = text.replace(match.group(1), "").strip()
    return grams, name


def format_kbju(calories, protein, fat, carbs):
    return f"{calories:.0f} ккал | Б: {protein:.1f}г Ж: {fat:.1f}г У: {carbs:.1f}г"


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я бот для подсчёта калорий 🥗\n\n"
        "Напиши мне продукт и граммы, например:\n"
        "«гречка 150» или «биг мак 200»\n"
        "Если продукта нет в базе — спрошу у ИИ.\n\n"
        "Пользуйся кнопками внизу для остальных действий 👇",
        reply_markup=main_menu(),
    )


@bot.message_handler(func=lambda m: m.text == BTN_FOODS)
def list_foods(message):
    names = ", ".join(FOODS.keys())
    bot.send_message(
        message.chat.id,
        f"Базовые продукты:\n{names}\n\nПлюс все продукты, которые ты добавил(а) через «{BTN_ADDFOOD}».",
    )


@bot.message_handler(func=lambda m: m.text == BTN_GOAL)
@bot.message_handler(commands=["setgoal"])
def setgoal_start(message):
    bot.send_message(
        message.chat.id,
        "Напиши норму в формате:\n"
        "калории белки жиры углеводы\n\n"
        "Например: 2000 120 60 250\n"
        "Можно указать только калории: 2000",
    )
    bot.register_next_step_handler(message, setgoal_save)


def setgoal_save(message):
    parts = message.text.replace(",", ".").split()
    try:
        calories = float(parts[0])
        protein = float(parts[1]) if len(parts) > 1 else None
        fat = float(parts[2]) if len(parts) > 2 else None
        carbs = float(parts[3]) if len(parts) > 3 else None
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Не понял формат. Попробуй ещё раз, например: 2000 120 60 250")
        return

    set_goal(message.from_user.id, calories, protein, fat, carbs)
    text = f"✅ Норма сохранена: {calories:.0f} ккал"
    if protein:
        text += f", Б: {protein:.0f}г Ж: {fat:.0f}г У: {carbs:.0f}г"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == BTN_ADDFOOD)
@bot.message_handler(commands=["addfood"])
def addfood_start(message):
    bot.send_message(
        message.chat.id,
        "Добавим продукт в твою базу. Напиши в формате (значения на 100г):\n"
        "название калории белки жиры углеводы\n\n"
        "Например: данон актимель клубника 72 2.8 1.5 12",
    )
    bot.register_next_step_handler(message, addfood_save)


def addfood_save(message):
    text = message.text.strip()
    match = re.search(r"(\d+[.,]?\d*)\s+(\d+[.,]?\d*)\s+(\d+[.,]?\d*)\s+(\d+[.,]?\d*)\s*$", text.replace(",", "."))
    if not match:
        bot.send_message(message.chat.id, "Не понял формат. Пример: протеиновый батончик 380 30 12 35")
        return

    name = text[:match.start()].strip()
    calories, protein, fat, carbs = (float(match.group(i)) for i in range(1, 5))

    add_custom_food(name, calories, protein, fat, carbs)
    bot.send_message(
        message.chat.id,
        f"✅ Добавил «{name}» в базу: {format_kbju(calories, protein, fat, carbs)} на 100г",
        reply_markup=main_menu(),
    )


@bot.message_handler(func=lambda m: m.text == BTN_TODAY)
@bot.message_handler(commands=["today"])
def today_summary(message):
    rows, total_cal, total_protein, total_fat, total_carbs = get_today_summary(message.from_user.id)

    if not rows:
        bot.send_message(message.chat.id, "Сегодня ты ещё ничего не записал(а).", reply_markup=main_menu())
        return

    lines = [f"— {r[0]} ({r[1]:.0f}г): {r[2]:.0f} ккал" for r in rows]
    text = "📊 Сводка за сегодня:\n\n" + "\n".join(lines)
    text += f"\n\nВсего: {format_kbju(total_cal, total_protein, total_fat, total_carbs)}"

    goal = get_goal(message.from_user.id)
    if goal:
        goal_cal, goal_protein, goal_fat, goal_carbs = goal
        remaining_cal = goal_cal - total_cal
        text += f"\n\n🎯 Норма: {goal_cal:.0f} ккал | Осталось: {remaining_cal:.0f} ккал"
        if goal_protein:
            text += (f"\nБелки: {total_protein:.0f}/{goal_protein:.0f}г | "
                     f"Жиры: {total_fat:.0f}/{goal_fat:.0f}г | "
                     f"Углеводы: {total_carbs:.0f}/{goal_carbs:.0f}г")
    else:
        text += f"\n\nСовет: задай дневную норму кнопкой «{BTN_GOAL}»"

    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda message: True)
def handle_food(message):
    grams, food_query = parse_grams_and_name(message.text)
    if grams is None:
        bot.send_message(
            message.chat.id,
            "Не вижу количество в граммах. Напиши, например: «гречка 150»",
            reply_markup=main_menu(),
        )
        return

    # 1. Ищем в базовой встроенной базе
    food_name, data = find_food(food_query)

    # 2. Если не нашли — ищем в базе, которую пользователь пополнял сам
    if not food_name:
        food_name, data = find_custom_food(food_query)

    # 3. Если и там нет — спрашиваем ИИ
    from_ai = False
    if not food_name:
        bot.send_message(message.chat.id, f"Не нашёл «{food_query}» в базе, спрашиваю у ИИ...")
        ai_result = ask_ai_for_food(food_query)
        if ai_result is None:
            bot.send_message(
                message.chat.id,
                f"Не получилось узнать у ИИ. Добавь продукт вручную кнопкой «{BTN_ADDFOOD}»",
                reply_markup=main_menu(),
            )
            return
        data = ai_result
        food_name = food_query.lower().strip()
        from_ai = True

    cal_100, protein_100, fat_100, carbs_100 = data
    factor = grams / 100

    calories = cal_100 * factor
    protein = protein_100 * factor
    fat = fat_100 * factor
    carbs = carbs_100 * factor

    add_entry(message.from_user.id, food_name, grams, calories, protein, fat, carbs)

    reply = f"✅ Записал: {food_name} ({grams:.0f}г)\n{format_kbju(calories, protein, fat, carbs)}"
    if from_ai:
        # Сохраняем в базу, чтобы в следующий раз не спрашивать ИИ заново
        add_custom_food(food_name, cal_100, protein_100, fat_100, carbs_100)
        reply += "\n\n(оценка от ИИ, сохранил в базу на будущее)"

    bot.send_message(message.chat.id, reply, reply_markup=main_menu())


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
