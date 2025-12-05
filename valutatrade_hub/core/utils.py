"""
Вспомогательные функции
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .currencies import get_currency
from .exceptions import CurrencyNotFoundError


def validate_currency_code(code: str) -> str:
    """Валидирует код валюты"""
    code = code.upper().strip()
    if not code:
        raise ValueError("Код валюты не может быть пустым")

    # Попробуем найти валюту в реестре
    try:
        get_currency(code)
    except CurrencyNotFoundError:
        # Если не нашли, просто проверяем формат
        if not (2 <= len(code) <= 5):
            raise ValueError("Код валюты должен содержать от 2 до 5 символов")
        if " " in code:
            raise ValueError("Код валюты не должен содержать пробелы")

    return code


def validate_amount(amount: float) -> float:
    """Валидирует сумму"""
    amount = float(amount)
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
    return amount


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Загружает JSON файл"""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def save_json_file(file_path: Path, data: Dict[str, Any]):
    """Сохраняет данные в JSON файл"""
    # Создаем директорию если не существует
    file_path.parent.mkdir(exist_ok=True)

    # Сохраняем во временный файл, затем переименовываем
    temp_path = file_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    temp_path.rename(file_path)


def is_rate_fresh(updated_at: str, ttl_seconds: int) -> bool:
    """Проверяет, не устарел ли курс"""
    try:
        update_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        now = datetime.now(update_time.tzinfo) if update_time.tzinfo else datetime.now()
        age = now - update_time
        return age.total_seconds() < ttl_seconds
    except (ValueError, TypeError):
        return False


def format_currency_value(value: float, currency_code: str) -> str:
    """Форматирует денежное значение"""
    if currency_code in ["BTC", "ETH", "SOL"]:
        # Криптовалюты - больше знаков после запятой
        return f"{value:.6f} {currency_code}"
    else:
        # Фиатные валюты - 2 знака
        return f"{value:.2f} {currency_code}"
