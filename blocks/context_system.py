from datetime import datetime
import pytz


def get_time_context():
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(kyiv_tz)

    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "year": now.year
    }


def get_location_context():
    return {
        "country": "Украина",
        "timezone": "Europe/Kyiv",
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
Ты находишься в реальном текущем времени.
Отвечай, исходя из актуальной даты и времени.
Не используй устаревшие данные.
"""
