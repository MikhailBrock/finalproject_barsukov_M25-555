import logging
from typing import Optional, Tuple, Dict
from datetime import datetime
from valutatrade_hub.core.models import User, Portfolio
from valutatrade_hub.core.currencies import CurrencyRegistry
from valutatrade_hub.core.exceptions import (
    InsufficientFundsError, CurrencyNotFoundError, 
    ValidationError, PortfolioNotFoundError
)
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader

logger = logging.getLogger('valutatrade.usecases')
db = DatabaseManager()
settings = SettingsLoader()


class UserUseCases:
    """Сценарии использования для работы с пользователями"""
    
    @staticmethod
    @log_action('REGISTER')
    def register_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Регистрация нового пользователя"""
        # Валидация имени пользователя
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long", None
        
        # Проверка уникальности username
        existing_user = db.get_user_by_username(username)
        if existing_user:
            return False, f"Username '{username}' already taken", None
        
        # Валидация пароля
        if len(password) < 4:
            return False, "Password must be at least 4 characters long", None
        
        # Генерация user_id
        all_users = db.get_all_users()
        user_id = max([user.user_id for user in all_users], default=0) + 1
        
        # Хеширование пароля
        import hashlib
        import os
        salt = os.urandom(16).hex()
        hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Создание пользователя
        user = User(
            user_id=user_id,
            username=username,
            hashed_password=hashed_password,
            salt=salt,
            registration_date=datetime.now()
        )
        
        # Сохранение пользователя
        db.save_user(user)
        
        # Создание портфеля с начальным балансом
        portfolio = Portfolio(user_id=user_id)
        portfolio.add_wallet('USD', 1000.0)  # Начальный баланс
        db.save_portfolio(portfolio)
        
        logger.info(f"User {username} registered with ID {user_id}")
        return True, f"User '{username}' registered successfully (id={user_id})", user
    
    @staticmethod
    @log_action('LOGIN')
    def login_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Аутентификация пользователя"""
        user = db.get_user_by_username(username)
        if not user:
            return False, f"User '{username}' not found", None
        
        if not user.verify_password(password):
            return False, "Invalid password", None
        
        logger.info(f"User {username} logged in")
        return True, f"Logged in as '{username}'", user
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Изменение пароля пользователя"""
        user = db.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        
        if not user.verify_password(old_password):
            return False, "Invalid current password"
        
        if len(new_password) < 4:
            return False, "New password must be at least 4 characters long"
        
        user.change_password(new_password)
        db.save_user(user)
        
        logger.info(f"User {user.username} changed password")
        return True, "Password changed successfully"


class PortfolioUseCases:
    """Сценарии использования для работы с портфелями"""
    
    @staticmethod
    @log_action('SHOW_PORTFOLIO')
    def get_portfolio_info(user_id: int, base_currency: str = 'USD') -> Tuple[bool, str, Optional[Dict]]:
        """Получение информации о портфеле пользователя"""
        portfolio = db.get_portfolio_by_user_id(user_id)
        if not portfolio:
            return False, "Portfolio not found", None
        
        if not portfolio.wallets:
            return True, "Portfolio is empty", {"total_value": 0.0, "wallets": []}
        
        # Получаем курсы валют
        rates = db.get_exchange_rates()
        
        # Рассчитываем стоимость каждого кошелька и общую стоимость
        wallets_info = []
        total_value = 0.0
        exchange_rates = {}
        
        # Преобразуем rates в простой словарь для быстрого доступа
        for rate_key, rate_data in rates.items():
            exchange_rates[rate_key] = rate_data.get('rate', 0)
        
        for currency, wallet in portfolio.wallets.items():
            balance = wallet.balance
            if currency == base_currency:
                value = balance
            else:
                rate_key = f"{currency}_{base_currency}"
                if rate_key in exchange_rates:
                    rate = exchange_rates[rate_key]
                else:
                    # Пробуем обратную пару
                    reverse_key = f"{base_currency}_{currency}"
                    if reverse_key in exchange_rates:
                        rate = 1.0 / exchange_rates[reverse_key]
                    else:
                        rate = 0
                value = balance * rate
            
            wallets_info.append({
                'currency': currency,
                'balance': balance,
                'value_in_base': value,
                'rate_used': rate if currency != base_currency else 1.0
            })
            total_value += value
        
        result = {
            'user_id': user_id,
            'base_currency': base_currency,
            'total_value': total_value,
            'wallets': wallets_info,
            'timestamp': datetime.now().isoformat()
        }
        
        return True, "Portfolio retrieved successfully", result
    
    @staticmethod
    def format_portfolio_display(portfolio_data: Dict) -> str:
        """Форматирует данные портфеля для отображения"""
        from prettytable import PrettyTable
        
        table = PrettyTable()
        table.field_names = ["Currency", "Balance", f"Value ({portfolio_data['base_currency']})", "Rate Used"]
        table.align["Currency"] = "l"
        table.align["Balance"] = "r"
        table.align[f"Value ({portfolio_data['base_currency']})"] = "r"
        table.align["Rate Used"] = "r"
        
        for wallet in portfolio_data['wallets']:
            table.add_row([
                wallet['currency'],
                f"{wallet['balance']:.4f}",
                f"{wallet['value_in_base']:.2f}",
                f"{wallet['rate_used']:.6f}" if wallet['rate_used'] != 1.0 else "1.0"
            ])
        
        result = f"Portfolio (base: {portfolio_data['base_currency']}):\n"
        result += str(table)
        result += f"\n{'='*50}\n"
        result += f"TOTAL VALUE: {portfolio_data['total_value']:.2f} {portfolio_data['base_currency']}\n"
        result += f"Updated: {portfolio_data['timestamp']}"
        
        return result
    
    @staticmethod
    @log_action('BUY', verbose=True)
    def buy_currency(user_id: int, currency_code: str, amount: float) -> Tuple[bool, str, Optional[Dict]]:
        """Покупка валюты"""
        try:
            # Валидация валюты
            CurrencyRegistry.get_currency(currency_code)
            
            if amount <= 0:
                raise ValidationError("amount", "must be positive")
            
            if currency_code == 'USD':
                raise ValidationError("currency", "cannot buy USD with USD")
            
            # Получаем портфель
            portfolio = db.get_portfolio_by_user_id(user_id)
            if not portfolio:
                raise PortfolioNotFoundError(user_id)
            
            # Получаем курс
            rate = db.get_exchange_rate(currency_code, 'USD')
            if not rate:
                raise CurrencyNotFoundError(f"{currency_code}_USD")
            
            cost_usd = amount * rate
            
            # Проверяем USD кошелек
            usd_wallet = portfolio.get_wallet('USD')
            if not usd_wallet:
                usd_wallet = portfolio.add_wallet('USD', 0.0)
            
            if usd_wallet.balance < cost_usd:
                raise InsufficientFundsError(usd_wallet.balance, cost_usd, 'USD')
            
            # Запоминаем старые балансы для логов
            old_usd_balance = usd_wallet.balance
            old_currency_balance = portfolio.get_wallet(currency_code)
            old_currency_balance = old_currency_balance.balance if old_currency_balance else 0.0
            
            # Выполняем покупку
            usd_wallet.withdraw(cost_usd)
            
            # Получаем или создаем кошелек для покупаемой валюты
            currency_wallet = portfolio.get_wallet(currency_code)
            if not currency_wallet:
                currency_wallet = portfolio.add_wallet(currency_code, 0.0)
            
            currency_wallet.deposit(amount)
            
            # Сохраняем изменения
            db.save_portfolio(portfolio)
            
            # Формируем результат
            result = {
                'operation': 'buy',
                'currency': currency_code,
                'amount': amount,
                'rate': rate,
                'cost_usd': cost_usd,
                'old_usd_balance': old_usd_balance,
                'new_usd_balance': usd_wallet.balance,
                'old_currency_balance': old_currency_balance,
                'new_currency_balance': currency_wallet.balance,
                'timestamp': datetime.now().isoformat()
            }
            
            return True, "Buy operation completed successfully", result
            
        except Exception as e:
            logger.error(f"Buy operation failed: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    @staticmethod
    @log_action('SELL', verbose=True)
    def sell_currency(user_id: int, currency_code: str, amount: float) -> Tuple[bool, str, Optional[Dict]]:
        """Продажа валюты"""
        try:
            # Валидация валюты
            CurrencyRegistry.get_currency(currency_code)
            
            if amount <= 0:
                raise ValidationError("amount", "must be positive")
            
            if currency_code == 'USD':
                raise ValidationError("currency", "cannot sell USD for USD")
            
            # Получаем портфель
            portfolio = db.get_portfolio_by_user_id(user_id)
            if not portfolio:
                raise PortfolioNotFoundError(user_id)
            
            # Проверяем наличие валюты
            currency_wallet = portfolio.get_wallet(currency_code)
            if not currency_wallet:
                raise ValidationError("currency", f"you don't have {currency_code} wallet")
            
            if currency_wallet.balance < amount:
                raise InsufficientFundsError(currency_wallet.balance, amount, currency_code)
            
            # Получаем курс
            rate = db.get_exchange_rate(currency_code, 'USD')
            if not rate:
                raise CurrencyNotFoundError(f"{currency_code}_USD")
            
            revenue_usd = amount * rate
            
            # Запоминаем старые балансы для логов
            old_currency_balance = currency_wallet.balance
            old_usd_balance = portfolio.get_wallet('USD')
            old_usd_balance = old_usd_balance.balance if old_usd_balance else 0.0
            
            # Выполняем продажу
            currency_wallet.withdraw(amount)
            
            # Получаем или создаем USD кошелек
            usd_wallet = portfolio.get_wallet('USD')
            if not usd_wallet:
                usd_wallet = portfolio.add_wallet('USD', 0.0)
            
            usd_wallet.deposit(revenue_usd)
            
            # Сохраняем изменения
            db.save_portfolio(portfolio)
            
            # Формируем результат
            result = {
                'operation': 'sell',
                'currency': currency_code,
                'amount': amount,
                'rate': rate,
                'revenue_usd': revenue_usd,
                'old_currency_balance': old_currency_balance,
                'new_currency_balance': currency_wallet.balance,
                'old_usd_balance': old_usd_balance,
                'new_usd_balance': usd_wallet.balance,
                'timestamp': datetime.now().isoformat()
            }
            
            return True, "Sell operation completed successfully", result
            
        except Exception as e:
            logger.error(f"Sell operation failed: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    @staticmethod
    def format_operation_display(operation_data: Dict) -> str:
        """Форматирует данные операции для отображения"""
        if operation_data['operation'] == 'buy':
            return (
                f"Successfully bought {operation_data['amount']:.4f} {operation_data['currency']} "
                f"for {operation_data['cost_usd']:.2f} USD\n"
                f"Rate: {operation_data['rate']:.6f} {operation_data['currency']}/USD\n"
                f"{operation_data['currency']}: {operation_data['old_currency_balance']:.4f} → "
                f"{operation_data['new_currency_balance']:.4f}\n"
                f"USD: {operation_data['old_usd_balance']:.2f} → {operation_data['new_usd_balance']:.2f}"
            )
        else:  # sell
            return (
                f"Successfully sold {operation_data['amount']:.4f} {operation_data['currency']} "
                f"for {operation_data['revenue_usd']:.2f} USD\n"
                f"Rate: {operation_data['rate']:.6f} {operation_data['currency']}/USD\n"
                f"{operation_data['currency']}: {operation_data['old_currency_balance']:.4f} → "
                f"{operation_data['new_currency_balance']:.4f}\n"
                f"USD: {operation_data['old_usd_balance']:.2f} → {operation_data['new_usd_balance']:.2f}"
            )


class RatesUseCases:
    """Сценарии использования для работы с курсами валют"""
    
    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Tuple[bool, str, Optional[Dict]]:
        """Получение курса обмена между валютами"""
        try:
            # Валидация валют
            CurrencyRegistry.get_currency(from_currency)
            CurrencyRegistry.get_currency(to_currency)
            
            # Получаем курс из базы
            rate = db.get_exchange_rate(from_currency, to_currency)
            
            if not rate:
                return False, f"Exchange rate {from_currency}→{to_currency} not found", None
            
            # Получаем информацию о курсе
            rates = db.get_exchange_rates()
            rate_key = f"{from_currency}_{to_currency}"
            rate_data = rates.get(rate_key, {})
            
            result = {
                'from_currency': from_currency,
                'to_currency': to_currency,
                'rate': rate,
                'updated_at': rate_data.get('updated_at', 'Unknown'),
                'source': rate_data.get('source', 'Unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
            return True, "Exchange rate retrieved successfully", result
            
        except CurrencyNotFoundError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Failed to get exchange rate: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    @staticmethod
    def format_rate_display(rate_data: Dict) -> str:
        """Форматирует данные курса для отображения"""
        return (
            f"Exchange Rate:\n"
            f"{rate_data['from_currency']} → {rate_data['to_currency']}: {rate_data['rate']:.6f}\n"
            f"Updated: {rate_data['updated_at']}\n"
            f"Source: {rate_data['source']}"
        )
    
    @staticmethod
    def check_rates_freshness() -> Tuple[bool, str]:
        """Проверяет свежесть курсов валют"""
        rates = db.get_exchange_rates()
        if not rates:
            return False, "No exchange rates available"
        
        # Получаем TTL из настроек
        rates_ttl = settings.get('rates_ttl_seconds', 300)
        
        # Проверяем время последнего обновления
        rates_info = db._read_json(db.data_dir + '/rates.json')
        last_refresh = rates_info.get('last_refresh')
        
        if not last_refresh:
            return False, "Last refresh time not available"
        
        try:
            last_refresh_time = datetime.fromisoformat(last_refresh)
            now = datetime.now()
            age = (now - last_refresh_time).total_seconds()
            
            if age > rates_ttl:
                return False, f"Exchange rates are outdated ({age:.0f}s old, TTL: {rates_ttl}s)"
            else:
                return True, f"Exchange rates are fresh ({age:.0f}s old)"
                
        except Exception as e:
            logger.error(f"Failed to check rates freshness: {str(e)}")
            return False, f"Error checking rates freshness: {str(e)}"