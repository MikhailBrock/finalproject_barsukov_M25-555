"""
Операции с хранилищем данных
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from .config import config


class StorageManager:
    """Менеджер хранилища данных"""

    def load_rates(self) -> Dict[str, Any]:
        """Загружает текущие курсы из файла"""
        try:
            if config.RATES_FILE_PATH.exists():
                with open(config.RATES_FILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка загрузки rates.json: {e}")

        return {"pairs": {}, "last_refresh": None}

    def save_rates(self, rates_data: Dict[str, Any]):
        """Сохраняет текущие курсы в файл"""
        try:
            # Создаем структуру данных
            data = {
                "pairs": rates_data.get("pairs", {}),
                "last_refresh": rates_data.get("last_refresh"),
                "source": rates_data.get("source", "ParserService"),
            }

            # Сохраняем во временный файл, затем переименовываем
            temp_path = config.RATES_FILE_PATH.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            temp_path.rename(config.RATES_FILE_PATH)
            print(f"Сохранено {len(data['pairs'])} курсов в {config.RATES_FILE_PATH}")

        except Exception as e:
            print(f"Ошибка сохранения rates.json: {e}")
            raise

    def load_history(self) -> List[Dict[str, Any]]:
        """Загружает исторические данные"""
        try:
            if config.HISTORY_FILE_PATH.exists():
                with open(config.HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("history", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка загрузки exchange_rates.json: {e}")

        return []

    def save_to_history(self, rate_record: Dict[str, Any]):
        """Сохраняет запись в исторические данные"""
        try:
            history = self.load_history()
            history.append(rate_record)

            data = {"history": history, "last_updated": datetime.now().isoformat()}

            # Сохраняем во временный файл
            temp_path = config.HISTORY_FILE_PATH.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            temp_path.rename(config.HISTORY_FILE_PATH)

        except Exception as e:
            print(f"Ошибка сохранения в историю: {e}")
            raise

    def create_rate_record(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        source: str,
        meta: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Создает запись о курсе для сохранения в истории"""
        timestamp = datetime.now().isoformat() + "Z"
        record_id = f"{from_currency}_{to_currency}_{timestamp.replace(':', '-')}"

        return {
            "id": record_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "timestamp": timestamp,
            "source": source,
            "meta": meta or {},
        }
