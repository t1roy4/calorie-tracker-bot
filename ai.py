import os
import json
from anthropic import Anthropic

# Ключ берётся из переменной окружения ANTHROPIC_API_KEY (настроим в шаге запуска)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"  # быстрая и дешёвая модель, для такой задачи достаточно


def ask_ai_for_food(food_description: str):
    """
    Просит ИИ оценить калорийность и БЖУ продукта на 100г.
    Возвращает (calories, protein, fat, carbs) или None, если не получилось.
    """
    prompt = (
        f'Оцени пищевую ценность продукта "{food_description}" на 100 грамм. '
        "Ответь ТОЛЬКО в формате JSON без пояснений и без markdown-разметки, "
        'например: {"calories": 150, "protein": 10, "fat": 5, "carbs": 20}. '
        "Все значения — числа (калории в ккал, БЖУ в граммах)."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # на случай если модель всё же обернёт ответ в ```json ... ```
        text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)
        return (
            float(data["calories"]),
            float(data["protein"]),
            float(data["fat"]),
            float(data["carbs"]),
        )
    except Exception as e:
        print(f"Ошибка запроса к ИИ: {e}")
        return None
