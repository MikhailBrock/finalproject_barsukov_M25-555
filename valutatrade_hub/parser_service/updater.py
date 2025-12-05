"""
Основной модуль обновления курсов
"""

from datetime import datetime
from typing import Any, Dict

from .api_clients import CoinGeckoClient, ExchangeRateApiClient, MockApiClient
from .config import config
from .storage import StorageManager


class RatesUpdater:
    """Класс для обновления курсов валют"""

    def __init__(self):
        self.config = config
        self.storage = StorageManager()

        # Инициализируем клиентов
        self.clients = []

        # Добавляем CoinGecko клиент
        if config.CRYPTO_CURRENCIES:
            self.clients.append(CoinGeckoClient())

        # Добавляем ExchangeRate API клиент если есть ключ
        if config.EXCHANGERATE_API_KEY and config.FIAT_CURRENCIES:
            self.clients.append(ExchangeRateApiClient())

        # если нет клиентов, то используем Mock
        if not self.clients:
            self.clients.append(MockApiClient())

    def run_update(self) -> Dict[str, Any]:
        """Запускает процесс обновления курсов"""
        print("Запуск обновления курсов валют...")

        all_rates = {}
        successful_clients = 0
        total_rates = 0

        for client in self.clients:
            client_name = client.__class__.__name__
            print(f"Получение данных от {client_name}...", end=" ")

            try:
                rates = client.fetch_rates()
                all_rates.update(rates)
                successful_clients += 1
                total_rates += len(rates)
                print(f"OK ({len(rates)} курсов)")

                # Сохраняем в историю
                for pair, rate in rates.items():
                    from_curr, to_curr = pair.split("_")
                    record = self.storage.create_rate_record(
                        from_currency=from_curr,
                        to_currency=to_curr,
                        rate=rate,
                        source=client_name,
                        meta={"success": True},
                    )
                    self.storage.save_to_history(record)

            except Exception as e:
                print(f"ОШИБКА: {e}")
                # Продолжаем работу с другими клиентами

        if not all_rates:
            print("Не удалось получить ни одного курса")
            return {"success": False, "total_rates": 0, "last_refresh": None}

        # Формируем данные для сохранения
        rates_data = {
            "pairs": {},
            "last_refresh": datetime.now().isoformat(),
            "source": "ParserService",
        }

        for pair, rate in all_rates.items():
            rates_data["pairs"][pair] = {
                "rate": rate,
                "updated_at": datetime.now().isoformat(),
                "source": "ParserService",
            }

        # Сохраняем текущие курсы
        self.storage.save_rates(rates_data)

        print("\nОбновление завершено.")
        print(f"Успешных источников: {successful_clients}/{len(self.clients)}")
        print(f"Всего курсов: {total_rates}")

        return {
            "success": True,
            "total_rates": total_rates,
            "last_refresh": rates_data["last_refresh"],
        }
