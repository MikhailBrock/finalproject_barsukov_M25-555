import argparse
import json
import os
import hashlib
from datetime import datetime
import logging
from valutatrade_hub.core.currencies import CurrencyRegistry
from valutatrade_hub.core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.decorators import log_action
from valutatrade_hub.logging_config import setup_logging

# Инициализируем логирование
setup_logging()
logger = logging.getLogger('valutatrade.cli')

class CLIInterface:
    def __init__(self):
        self.current_user = None
        self.settings = SettingsLoader()  # Singleton настроек
        self.data_dir = self.settings.get('data_dir', 'data')
        self.session_file = os.path.join(self.data_dir, "session.json")
        self._ensure_data_files()
        self._load_session()
        logger.info("CLIInterface initialized")
    
    def _ensure_data_files(self):
        """Создает необходимые JSON файлы если их нет"""
        os.makedirs(self.data_dir, exist_ok=True)
    
        # Получаем список известных валют из реестра
        known_currencies = CurrencyRegistry.list_currencies()
    
        # Создаем базовые курсы для всех известных валют
        pairs = {}
        for currency in known_currencies:
            if currency != 'USD':
                pairs[f"{currency}_USD"] = {
                    "rate": 1.0 if currency == 'USD' else 
                            0.93 if currency == 'EUR' else
                            0.011 if currency == 'RUB' else
                            50000.0 if currency == 'BTC' else
                            3000.0 if currency == 'ETH' else 1.0,
                    "updated_at": datetime.now().isoformat(), 
                    "source": "Manual"
                }
    
        files = {
            'users.json': [],
            'portfolios.json': [],
            'rates.json': {
                "pairs": pairs,
                "last_refresh": datetime.now().isoformat(),
                "source": "Manual"
            },
            'session.json': {}
        }
    
        for filename, default_content in files.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, indent=2, ensure_ascii=False)
                logger.debug(f"Created {filepath}")
            else:
                # Обновляем существующий rates.json если нужно
                if filename == 'rates.json':
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    # Добавляем недостающие пары валют
                    if 'USD_EUR' not in existing_data.get('pairs', {}):
                        existing_data['pairs']['USD_EUR'] = {"rate": 0.93, "updated_at": datetime.now().isoformat(), "source": "Manual"}
                    if 'USD_BTC' not in existing_data.get('pairs', {}):
                        existing_data['pairs']['USD_BTC'] = {"rate": 0.00002, "updated_at": datetime.now().isoformat(), "source": "Manual"}
                    self._save_json('rates.json', existing_data)
    
    def _load_session(self):
        """Загружает сессию из файла"""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                if session_data and 'user_id' in session_data:
                    # Загружаем данные пользователя из users.json
                    users = self._load_json('users.json')
                    self.current_user = next(
                        (user for user in users if user['user_id'] == session_data['user_id']), 
                        None
                    )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.current_user = None
    
    def _save_session(self, user_data=None):
        """Сохраняет сессию в файл"""
        session_data = {}
        if user_data:
            session_data = {'user_id': user_data['user_id']}
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    
    def _clear_session(self):
        """Очищает сессию"""
        self.current_user = None
        self._save_session()
    
    def _load_json(self, filename):
        """Загружает данные из JSON файла"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return [] if filename in ['users.json', 'portfolios.json'] else {}
    
    def _save_json(self, filename, data):
        """Сохраняет данные в JSON файл"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _hash_password(self, password, salt=None):
        """Хеширует пароль с солью"""
        if salt is None:
            salt = os.urandom(16).hex()
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed, salt
    
    @log_action('REGISTER', verbose=True)
    def register(self, username, password):
        """Регистрация нового пользователя"""
        users = self._load_json('users.json')
    
        # Проверка уникальности username
        if any(user.get('username') == username for user in users):
            return False, f"Username '{username}' already taken"
    
        # Проверка длины пароля
        if len(password) < 4:
            return False, "Password must be at least 4 characters long"
    
        # Генерация user_id
        user_ids = [user.get('user_id', 0) for user in users]
        user_id = max(user_ids, default=0) + 1
    
        # Хеширование пароля
        hashed_password, salt = self._hash_password(password)
    
        # Создание пользователя
        new_user = {
            'user_id': user_id,
            'username': username,
            'hashed_password': hashed_password,
            'salt': salt,
            'registration_date': datetime.now().isoformat()
        }
    
        users.append(new_user)
        self._save_json('users.json', users)
    
        # Создание пустого портфеля
        portfolios = self._load_json('portfolios.json')
        new_portfolio = {
            'user_id': user_id,
            'wallets': {
                'USD': {'balance': 1000.0}  # Начальный баланс
            }
        }
        portfolios.append(new_portfolio)
        self._save_json('portfolios.json', portfolios)
    
        logger.info(f"User {username} registered successfully")
        return True, f"User '{username}' registered successfully (id={user_id})"
    
    @log_action('LOGIN')
    def login(self, username, password):
        """Аутентификация пользователя"""
        users = self._load_json('users.json')
        
        user_data = next((user for user in users if user.get('username') == username), None)
        if not user_data:
            return False, f"User '{username}' not found"
        
        # Проверка пароля
        test_hash, _ = self._hash_password(password, user_data.get('salt'))
        if test_hash != user_data.get('hashed_password'):
            return False, "Invalid password"
        
        self.current_user = user_data
        self._save_session(user_data)
        logger.info(f"User {username} logged in")
        return True, f"Logged in as '{username}'"
    
    def logout(self):
        """Выход из системы"""
        if self.current_user:
            username = self.current_user.get('username')
            self._clear_session()
            return f"Logged out from '{username}'"
        return "Not logged in"
    
    def _require_login(self):
        """Проверяет, что пользователь авторизован"""
        if not self.current_user:
            raise PermissionError("Please login first. Use: poetry run valutatrade login --username USERNAME --password PASSWORD")
    
    def show_portfolio(self, base_currency='USD'):
        """Показывает портфель пользователя"""
        self._require_login()
        
        portfolios = self._load_json('portfolios.json')
        user_portfolio = next(
            (p for p in portfolios if p.get('user_id') == self.current_user.get('user_id')), 
            None
        )
        
        if not user_portfolio or not user_portfolio.get('wallets'):
            return "Portfolio is empty"
        
        # Загружаем курсы из rates.json
        rates_data = self._load_json('rates.json')
        rates = rates_data.get('pairs', {})
        
        result = f"Portfolio of user '{self.current_user['username']}' (base: {base_currency}):\n"
        total_value = 0.0
        
        for currency, wallet_data in user_portfolio['wallets'].items():
            balance = wallet_data['balance']
            if currency == base_currency:
                value = balance
            else:
                rate_key = f"{currency}_{base_currency}"
                rate_data = rates.get(rate_key, {})
                rate = rate_data.get('rate', 0)
                value = balance * rate
            total_value += value
            result += f"- {currency}: {balance:.2f} → {value:.2f} {base_currency}\n"
        
        result += f"{'-'*40}\nTOTAL: {total_value:.2f} {base_currency}"
        return result

    # buy/sell операции
    @log_action('BUY', verbose=True)
    def buy_currency(self, currency, amount):
        """Покупка валюты"""
        self._require_login()
        
        try:
            # Валидация с использованием реестра валют
            currency_obj = CurrencyRegistry.get_currency(currency)
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if currency == 'USD':
                raise ValueError("Cannot buy USD with USD")
            
            # Загружаем данные
            portfolios = self._load_json('portfolios.json')
            user_portfolio = next(
                (p for p in portfolios if p.get('user_id') == self.current_user.get('user_id')), 
                None
            )
            
            if not user_portfolio:
                raise ValueError("Portfolio not found")
            
            # Получаем курс
            rates_data = self._load_json('rates.json')
            rate_key = f"{currency}_USD"
            rate_data = rates_data.get('pairs', {}).get(rate_key, {})
            
            if not rate_data:
                raise CurrencyNotFoundError(currency)
            
            rate = rate_data.get('rate', 0)
            if rate <= 0:
                raise ValueError(f"Invalid exchange rate for {currency}")
            
            cost_usd = amount * rate
            
            # Проверяем достаточно ли USD
            usd_balance = user_portfolio['wallets'].get('USD', {}).get('balance', 0)
            if usd_balance < cost_usd:
                raise InsufficientFundsError(usd_balance, cost_usd, 'USD')
            
            # ВЫПОЛНЯЕМ ПОКУПКУ
            old_usd = usd_balance
            old_currency = user_portfolio['wallets'].get(currency, {}).get('balance', 0)
            
            # 1. Снимаем USD
            user_portfolio['wallets']['USD']['balance'] = old_usd - cost_usd
            
            # 2. Добавляем купленную валюту
            if currency not in user_portfolio['wallets']:
                user_portfolio['wallets'][currency] = {'balance': 0}
            
            user_portfolio['wallets'][currency]['balance'] = old_currency + amount
            
            # Сохраняем изменения
            self._save_json('portfolios.json', portfolios)
            
            result = (f"Successfully bought {amount:.4f} {currency} for {cost_usd:.2f} USD\n"
                     f"   Rate: {rate} {currency}/USD\n"
                     f"   {currency}: {old_currency:.4f} → {old_currency + amount:.4f}\n"
                     f"   USD: {old_usd:.2f} → {old_usd - cost_usd:.2f}")
            
            logger.info(f"Buy operation completed: {amount} {currency} at rate {rate}")
            return result
            
        except (CurrencyNotFoundError, InsufficientFundsError, ValueError) as e:
            logger.error(f"Buy operation failed: {str(e)}")
            return f"Error: {str(e)}"
    
    @log_action('SELL', verbose=True)
    def sell_currency(self, currency, amount):
        """Продажа валюты"""
        self._require_login()
        
        try:
            # Валидация с использованием реестра валют
            currency_obj = CurrencyRegistry.get_currency(currency)
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if currency == 'USD':
                raise ValueError("Cannot sell USD for USD")
            
            # Загружаем данные
            portfolios = self._load_json('portfolios.json')
            user_portfolio = next(
                (p for p in portfolios if p.get('user_id') == self.current_user.get('user_id')), 
                None
            )
            
            if not user_portfolio:
                raise ValueError("Portfolio not found")
            
            # Проверяем наличие валюты
            if currency not in user_portfolio['wallets']:
                raise ValueError(f"You don't have {currency} wallet")
            
            currency_balance = user_portfolio['wallets'][currency]['balance']
            if currency_balance < amount:
                raise InsufficientFundsError(currency_balance, amount, currency)
            
            # Получаем курс
            rates_data = self._load_json('rates.json')
            rate_key = f"{currency}_USD"
            rate_data = rates_data.get('pairs', {}).get(rate_key, {})
            
            if not rate_data:
                raise CurrencyNotFoundError(currency)
            
            rate = rate_data.get('rate', 0)
            if rate <= 0:
                raise ValueError(f"Invalid exchange rate for {currency}")
            
            revenue_usd = amount * rate
            
            # ВЫПОЛНЯЕМ ПРОДАЖУ
            old_currency = currency_balance
            usd_balance = user_portfolio['wallets'].get('USD', {}).get('balance', 0)
            
            # 1. Снимаем проданную валюту
            user_portfolio['wallets'][currency]['balance'] = old_currency - amount
            
            # 2. Добавляем USD
            user_portfolio['wallets']['USD'] = {'balance': usd_balance + revenue_usd}
            
            # Сохраняем изменения
            self._save_json('portfolios.json', portfolios)
            
            result = (f"Successfully sold {amount:.4f} {currency} for {revenue_usd:.2f} USD\n"
                     f"   Rate: {rate} {currency}/USD\n"
                     f"   {currency}: {old_currency:.4f} → {old_currency - amount:.4f}\n"
                     f"   USD: {usd_balance:.2f} → {usd_balance + revenue_usd:.2f}")
            
            logger.info(f"Sell operation completed: {amount} {currency} at rate {rate}")
            return result
            
        except (CurrencyNotFoundError, InsufficientFundsError, ValueError) as e:
            logger.error(f"Sell operation failed: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_rate(self, from_currency, to_currency):
        rates_data = self._load_json('rates.json')
        rates = rates_data.get('pairs', {})
        
        rate_key = f"{from_currency}_{to_currency}"
        rate_data = rates.get(rate_key, {})
        
        if rate_data:
            rate = rate_data.get('rate', 'N/A')
            updated = rate_data.get('updated_at', 'Unknown')
            return f"Rate {from_currency}→{to_currency}: {rate} (updated: {updated})"
        else:
            return f"Rate {from_currency}→{to_currency} not found in cache"

    def run(self):
        """Основной цикл CLI"""
        parser = argparse.ArgumentParser(description='Currency Wallet CLI')
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Register command
        register_parser = subparsers.add_parser('register', help='Register new user')
        register_parser.add_argument('--username', required=True, help='Username')
        register_parser.add_argument('--password', required=True, help='Password')
        
        # Login command
        login_parser = subparsers.add_parser('login', help='Login to system')
        login_parser.add_argument('--username', required=True, help='Username')
        login_parser.add_argument('--password', required=True, help='Password')
        
        # Logout command
        subparsers.add_parser('logout', help='Logout from system')
        
        # Show portfolio command
        portfolio_parser = subparsers.add_parser('show-portfolio', help='Show user portfolio')
        portfolio_parser.add_argument('--base', default='USD', help='Base currency')
        
        # Buy command
        buy_parser = subparsers.add_parser('buy', help='Buy currency')
        buy_parser.add_argument('--currency', required=True, help='Currency code')
        buy_parser.add_argument('--amount', type=float, required=True, help='Amount to buy')
        
        # Sell command
        sell_parser = subparsers.add_parser('sell', help='Sell currency')
        sell_parser.add_argument('--currency', required=True, help='Currency code')
        sell_parser.add_argument('--amount', type=float, required=True, help='Amount to sell')
        
        # Get rate command
        rate_parser = subparsers.add_parser('get-rate', help='Get exchange rate')
        rate_parser.add_argument('--from', required=True, dest='from_currency', help='From currency')
        rate_parser.add_argument('--to', required=True, help='To currency')
        
        # Status command
        subparsers.add_parser('status', help='Show current session status')
        
        # List currencies command
        currencies_parser = subparsers.add_parser('list-currencies', help='List available currencies')

        # Currency info command
        info_parser = subparsers.add_parser('currency-info', help='Get currency information')
        info_parser.add_argument('--currency', required=True, help='Currency code')
        
        args = parser.parse_args()
        
        if args.command == 'register':
            success, message = self.register(args.username, args.password)
            print(message)
        
        elif args.command == 'login':
            success, message = self.login(args.username, args.password)
            print(message)
        
        elif args.command == 'logout':
            message = self.logout()
            print(message)
        
        elif args.command == 'show-portfolio':
            try:
                result = self.show_portfolio(args.base)
                print(result)
            except PermissionError as e:
                print(e)
        
        elif args.command == 'buy':
            try:
                result = self.buy_currency(args.currency, args.amount)
                print(result)
            except PermissionError as e:
                print(e)
        
        elif args.command == 'sell':
            try:
                result = self.sell_currency(args.currency, args.amount)
                print(result)
            except PermissionError as e:
                print(e)
        
        elif args.command == 'get-rate':
            result = self.get_rate(getattr(args, 'from_currency'), args.to)
            print(result)
        
        elif args.command == 'status':
            if self.current_user:
                print(f"Logged in as: {self.current_user.get('username')} (ID: {self.current_user.get('user_id')})")
            else:
                print("Not logged in")
        
        elif args.command == 'list-currencies':
            currencies = CurrencyRegistry.list_currencies()
            print("Available currencies:")
            for currency in currencies:
                info = CurrencyRegistry.get_currency_info(currency)
                print(f"  - {info}")
        
        elif args.command == 'currency-info':
            try:
                info = CurrencyRegistry.get_currency_info(args.currency)
                print(info)
            except ValueError as e:
                print(f"{str(e)}")
        
        else:
            parser.print_help()

def main():
    cli = CLIInterface()
    cli.run()

if __name__ == "__main__":
    main()