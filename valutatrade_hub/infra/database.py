"""
Singleton для управления JSON-хранилищем
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.models import Portfolio, User
from ..core.utils import load_json_file, save_json_file
from .settings import SettingsLoader


class DatabaseManager:
    """Менеджер базы данных (Singleton)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.settings = SettingsLoader()
            self._initialized = True

    def load_users(self) -> Dict[int, User]:
        """Загружает всех пользователей"""
        data = load_json_file(self.settings.users_file)
        users = {}

        for user_data in data.get("users", []):
            try:
                user = User.from_dict(user_data)
                users[user.user_id] = user
            except Exception as e:
                print(f"Ошибка загрузки пользователя: {e}")

        return users

    def save_users(self, users: Dict[int, User]):
        """Сохраняет всех пользователей"""
        data = {"users": [user.to_dict() for user in users.values()]}
        save_json_file(self.settings.users_file, data)

    def load_portfolios(self) -> Dict[int, Portfolio]:
        """Загружает все портфели"""
        data = load_json_file(self.settings.portfolios_file)
        portfolios = {}

        for portfolio_data in data.get("portfolios", []):
            try:
                portfolio = Portfolio.from_dict(portfolio_data)
                portfolios[portfolio.user_id] = portfolio
            except Exception as e:
                print(f"Ошибка загрузки портфеля: {e}")

        return portfolios

    def save_portfolios(self, portfolios: Dict[int, Portfolio]):
        """Сохраняет все портфели"""
        data = {
            "portfolios": [portfolio.to_dict() for portfolio in portfolios.values()]
        }
        save_json_file(self.settings.portfolios_file, data)

    def load_rates(self) -> Dict[str, Any]:
        """Загружает курсы валют"""
        return load_json_file(self.settings.rates_file)

    def save_rates(self, rates: Dict[str, Any]):
        """Сохраняет курсы валют"""
        save_json_file(self.settings.rates_file, rates)

    def load_exchange_rates(self) -> List[Dict[str, Any]]:
        """Загружает исторические курсы"""
        data = load_json_file(self.settings.exchange_rates_file)
        return data.get("history", [])

    def save_exchange_rate(self, rate_record: Dict[str, Any]):
        """Сохраняет одну запись исторического курса"""
        history = self.load_exchange_rates()
        history.append(rate_record)

        data = {"history": history, "last_updated": datetime.now().isoformat()}
        save_json_file(self.settings.exchange_rates_file, data)

    def get_next_user_id(self) -> int:
        """Генерирует следующий ID пользователя"""
        users = self.load_users()
        if not users:
            return 1
        return max(users.keys()) + 1

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Находит пользователя по имени"""
        users = self.load_users()
        for user in users.values():
            if user.username == username:
                return user
        return None

    def get_portfolio_by_user_id(self, user_id: int) -> Optional[Portfolio]:
        """Находит портфель по ID пользователя"""
        portfolios = self.load_portfolios()
        return portfolios.get(user_id)

    def save_user(self, user: User):
        """Сохраняет пользователя"""
        users = self.load_users()
        users[user.user_id] = user
        self.save_users(users)

    def save_portfolio(self, portfolio: Portfolio):
        """Сохраняет портфель"""
        portfolios = self.load_portfolios()
        portfolios[portfolio.user_id] = portfolio
        self.save_portfolios(portfolios)

    def create_user_portfolio(self, user_id: int):
        """Создает пустой портфель для пользователя"""
        portfolio = Portfolio(user_id)
        self.save_portfolio(portfolio)
        return portfolio
