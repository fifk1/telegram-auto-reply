# AI Model Configuration
MODEL_PATH = "model"

# AI Model Settings - Llama 3 RP tuned
AI_SETTINGS = {
    'temperature': 0.7,
    'top_p': 0.95,
    'max_new_tokens': 200,
    'repetition_penalty': 1.3,
}

# System Prompt - встроен в код
from datetime import datetime, timezone
from bisect import bisect_right

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
    _MSK_TZ = ZoneInfo("Europe/Moscow")
except Exception:  # fallback для окружений без zoneinfo
    _MSK_TZ = None

# Константы для оптимизации (вычисляются один раз при загрузке модуля)
_WEEKDAYS_RU = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
_TIME_BOUNDARIES = (7, 10, 14, 18, 23)
_WEEKDAY_ACTIVITIES = (
    "спишь или очень поздно бодрствуешь",
    "просыпаешься и собираешься на работу/учебу",
    "на работе или учебе",
    "занят работой или учебой",
    "дома после работы, занимаешься своими делами",
    "спишь или очень поздно бодрствуешь",
)
_WEEKEND_ACTIVITIES = (
    "спишь или очень поздно бодрствуешь",
    "просыпаешься, неспеша собираешься",
    "отдыхаешь или занимаешься своими делами",
    "дома, можешь работать или просто отдыхать",
    "дома, занимаешься своими делами",
    "спишь или очень поздно бодрствуешь",
)

def _get_default_prompt() -> str:
    """Возвращает базовый шаблон промпта по умолчанию"""
    return """[ROLEPLAY][STAY-IN-CHARACTER][NO-META][NO-EMOJI]
Ты — дружелюбный собеседник. Общаешься естественно и непринужденно.

[STYLE]
- Общение неформальное, обращайся на "ты"
- Будь естественным в ответах
- Задавай встречные вопросы по теме разговора
- Отвечай коротко, максимум 2 предложения

[CONTEXT]
- Сейчас время примерно: {CURRENT_TIME_MSK} ({DAY_OF_WEEK})
- Обычно в это время: {CURRENT_ACTIVITY}
- Твоё текущее состояние: {CURRENT_MOOD}
- Сейчас {SEASON}

Будь собой и общайся естественно. Никогда не упоминай, что ты искусственный интеллект. ВСЕГДА отвечай только на русском языке.
"""

# Используем встроенный промпт
SYSTEM_PROMPT_TEMPLATE = _get_default_prompt()

def get_system_prompt() -> str:
    """Возвращает системный промпт с актуальными датой/временем по Москве, активностью, настроением и сезоном."""
    # Получаем текущее время один раз
    if _MSK_TZ is not None:
        now = datetime.now(_MSK_TZ)
        current_time_msk = now.strftime("%d.%m.%Y %H:%M")
    else:
        now = datetime.now(timezone.utc)
        current_time_msk = now.strftime("%d.%m.%Y %H:%M") + " UTC"

    hour = now.hour
    weekday = now.weekday()  # 0=понедельник, 6=воскресенье
    month = now.month

    # День недели
    day_of_week = _WEEKDAYS_RU[weekday]
    is_weekend = weekday >= 5

    # Сезон (зима=12,1,2; весна=3,4,5; лето=6,7,8; осень=9,10,11)
    season = ("зима", "весна", "лето", "осень")[(month % 12) // 3]

    # Активность: выбираем массив по выходным/будням, затем индекс по времени
    activities = _WEEKEND_ACTIVITIES if is_weekend else _WEEKDAY_ACTIVITIES
    idx = bisect_right(_TIME_BOUNDARIES, hour)
    current_activity = activities[idx]

    # Настроение по времени суток
    if hour < 7 or hour >= 23:
        current_mood = "очень сонный" if hour < 3 else "засиделся, но уже поздно"
    elif hour < 10:
        current_mood = "немного сонный, но бодрый" if not is_weekend else "выспавшийся, расслабленный"
    elif hour < 14:
        current_mood = "активный, в работе или учёбе"
    elif hour < 18:
        current_mood = "уставший после учёбы, но ещё есть силы"
    else:  # 18-22
        current_mood = "расслабленный, отдыхаешь после дня"

    return SYSTEM_PROMPT_TEMPLATE.format(
        CURRENT_TIME_MSK=current_time_msk,
        DAY_OF_WEEK=day_of_week,
        CURRENT_ACTIVITY=current_activity,
        CURRENT_MOOD=current_mood,
        SEASON=season
    )
























































