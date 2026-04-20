from datetime import datetime

def get_time_context():
    now = datetime.now()

    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "year": now.year
    }


def get_location_context():
    return {
        "country": "Украина",
        "timezone": "GMT+3",
        "city": "не определён (по умолчанию Украина)"
    }


def build_context_text():
    time_data = get_time_context()
    loc = get_location_context()

    return f"""
ТЕКУЩИЙ КОНТЕКСТ:
- Дата: {time_data['date']}
- Время: {time_data['time']}
- Год: {time_data['year']}
- Часовой пояс: {loc['timezone']}
- Страна: {loc['country']}

ВАЖНО:
Ты находишься в текущем времени и должен отвечать, исходя из актуальной реальности.
Не используй устаревшие данные.
"""
