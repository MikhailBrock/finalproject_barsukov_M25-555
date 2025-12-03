import argparse
import json
import os
import sys
from datetime import datetime
import logging
from typing import Optional

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CurrencyRegistry
from valutatrade_hub.core.exceptions import (
    AuthenticationError
)
from valutatrade_hub.core.usecases import (
    UserUseCases, PortfolioUseCases, RatesUseCases
)
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.api_clients import ApiClientFactory
from valutatrade_hub.logging_config import setup_logging, LoggingMixin


# Настройка логирования
setup_logging()
logger = logging.getLogger('valutatrade.cli')


class CLIInterface(LoggingMixin):
    """Основной класс CLI интерфейса"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.settings = SettingsLoader()
        self.db = DatabaseManager()
        self.data_dir = self.settings.get('data_dir', 'data')
        self.session_file = os.path.join(self.data_dir, "session.json")
        
        # Инициализация парсера
        self.parser_config = ParserConfig()
        self.rates_storage = RatesStorage(self.parser_config)
        self.rates_updater = RatesUpdater(self.parser_config, self.rates_storage)
        
        self._ensure_data_files()
        self._load_session()
        
        self.log_info("CLIInterface initialized")
    
    def _ensure_data_files(self):
        """Создает необходимые файлы данных если их нет"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        files = {
            'users.json': [],
            'portfolios.json': [],
            'rates.json': {
                "pairs": {},
                "last_refresh": datetime.now().isoformat(),
                "source": "Manual"
            },
            'session.json': {},
            'transactions.json': [],
            'exchange_rates.json': []
        }
        
        for filename, default_content in files.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, indent=2, ensure_ascii=False)
                self.log_debug(f"Created {filepath}")
    
    def _load_session(self):
        """Загружает сессию пользователя из файла"""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            if session_data and 'user_id' in session_data:
                user_id = session_data['user_id']
                self.current_user = self.db.get_user_by_id(user_id)
                if self.current_user:
                    self.log_info(f"Session loaded for user: {self.current_user.username}")
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.current_user = None
    
    def _save_session(self, user_id: Optional[int] = None):
        """Сохраняет сессию пользователя в файл"""
        session_data = {}
        if user_id:
            session_data = {'user_id': user_id}
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    
    def _clear_session(self):
        """Очищает сессию пользователя"""
        self.current_user = None
        self._save_session()
    
    def _require_login(self):
        """Проверяет, что пользователь авторизован"""
        if not self.current_user:
            raise AuthenticationError("Please login first")
    
    # ==================== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ====================
    
    def handle_register(self, args):
        """Обработка команды регистрации"""
        success, message, user = UserUseCases.register_user(
            args.username, args.password
        )
        
        if success:
            print(f"{message}")
            print(f"Use 'login --username {args.username} --password {args.password}' to login")
        else:
            print(f"{message}")
    
    def handle_login(self, args):
        """Обработка команды входа в систему"""
        success, message, user = UserUseCases.login_user(
            args.username, args.password
        )
        
        if success and user:
            self.current_user = user
            self._save_session(user.user_id)
            print(f"{message}")
        else:
            print(f"{message}")
    
    def handle_logout(self, args):
        """Обработка команды выхода из системы"""
        if self.current_user:
            username = self.current_user.username
            self._clear_session()
            print(f"Logged out from '{username}'")
        else:
            print("Not logged in")
    
    def handle_status(self, args):
        """Обработка команды статуса"""
        if self.current_user:
            print(f"Logged in as: {self.current_user.username}")
            print(f"User ID: {self.current_user.user_id}")
            print(f"Registered: {self.current_user.registration_date}")
            
            # Информация о сессии
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    if 'user_id' in session_data:
                        print("   Session active: Yes")
            except:
                print("   Session active: No")
        else:
            print("Not logged in")
            print("Use 'login --username USERNAME --password PASSWORD' to login")
    
    # ==================== КОМАНДЫ ПОРТФЕЛЯ ====================
    
    def handle_show_portfolio(self, args):
        """Обработка команды показа портфеля"""
        try:
            self._require_login()
            
            success, message, portfolio_data = PortfolioUseCases.get_portfolio_info(
                self.current_user.user_id, args.base
            )
            
            if success:
                if portfolio_data['wallets']:
                    formatted = PortfolioUseCases.format_portfolio_display(portfolio_data)
                    print(formatted)
                else:
                    print("Portfolio is empty")
                    print("Use 'buy --currency CURRENCY --amount AMOUNT' to add currencies")
            else:
                print(f"{message}")
                
        except AuthenticationError as e:
            print(f"{str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def handle_buy(self, args):
        """Обработка команды покупки валюты"""
        try:
            self._require_login()
            
            success, message, operation_data = PortfolioUseCases.buy_currency(
                self.current_user.user_id, args.currency, args.amount
            )
            
            if success and operation_data:
                formatted = PortfolioUseCases.format_operation_display(operation_data)
                print(formatted)
            else:
                print(f"{message}")
                
        except AuthenticationError as e:
            print(f"{str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def handle_sell(self, args):
        """Обработка команды продажи валюты"""
        try:
            self._require_login()
            
            success, message, operation_data = PortfolioUseCases.sell_currency(
                self.current_user.user_id, args.currency, args.amount
            )
            
            if success and operation_data:
                formatted = PortfolioUseCases.format_operation_display(operation_data)
                print(formatted)
            else:
                print(f"{message}")
                
        except AuthenticationError as e:
            print(f"{str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # ==================== КОМАНДЫ КУРСОВ ВАЛЮТ ====================
    
    def handle_get_rate(self, args):
        """Обработка команды получения курса"""
        try:
            from_currency = getattr(args, 'from_currency')
            to_currency = args.to
            
            success, message, rate_data = RatesUseCases.get_exchange_rate(
                from_currency, to_currency
            )
            
            if success and rate_data:
                formatted = RatesUseCases.format_rate_display(rate_data)
                print(formatted)
                
                # Проверяем свежесть курсов
                freshness_result = RatesUseCases.check_rates_freshness()
                if not freshness_result[0]:
                    print(f"Warning: {freshness_result[1]}")
                    print("Use 'update-rates' to refresh rates")
            else:
                print(f"{message}")
                print("Use 'update-rates' to fetch latest rates")
                
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def handle_list_currencies(self, args):
        """Обработка команды списка валют"""
        try:
            currencies = CurrencyRegistry.list_currencies()
            
            table = PrettyTable()
            table.field_names = ["Code", "Name", "Type", "Info"]
            table.align["Code"] = "l"
            table.align["Name"] = "l"
            table.align["Type"] = "l"
            table.align["Info"] = "l"
            
            for currency_code in currencies:
                try:
                    currency = CurrencyRegistry.get_currency(currency_code)
                    currency_type = "Crypto" if hasattr(currency, 'algorithm') else "Fiat"
                    
                    # Сокращаем информацию для таблицы
                    info = currency.get_display_info()
                    if len(info) > 50:
                        info = info[:47] + "..."
                    
                    table.add_row([
                        currency_code,
                        currency.name,
                        currency_type,
                        info
                    ])
                except Exception:
                    table.add_row([currency_code, "Unknown", "Unknown", "Error"])
            
            print("Available Currencies:")
            print(table)
            print(f"\nTotal: {len(currencies)} currencies")
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def handle_currency_info(self, args):
        """Обработка команды информации о валюте"""
        try:
            info = CurrencyRegistry.get_currency_info(args.currency)
            print("Currency Information:")
            print(f"{info}")
            
            # Дополнительная информация
            currency_type = CurrencyRegistry.get_currency_type(args.currency)
            print(f"   Type: {currency_type.upper()}")
            
            # Проверяем наличие курса
            rate = self.db.get_exchange_rate(args.currency, 'USD')
            if rate:
                print(f"Current rate to USD: {rate:.6f}")
            else:
                print("Rate to USD: Not available")
                
        except ValueError as e:
            print(f"{str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # ==================== КОМАНДЫ ПАРСЕРА ====================
    
    def handle_update_rates(self, args):
        """Обработка команды обновления курсов"""
        try:
            print("Updating exchange rates...")
            
            # Используем указанный источник если задан
            if args.source:
                if args.source.lower() == 'coingecko':
                    client = ApiClientFactory.create_client(self.parser_config, 'coingecko')
                    self.rates_updater.clients = [client]
                elif args.source.lower() == 'exchangerate':
                    client = ApiClientFactory.create_client(self.parser_config, 'exchangerate')
                    self.rates_updater.clients = [client]
                elif args.source.lower() == 'mock':
                    client = ApiClientFactory.create_client(self.parser_config, 'mock')
                    self.rates_updater.clients = [client]
                else:
                    print(f"Unknown source: {args.source}")
                    print("Available sources: coingecko, exchangerate, mock")
                    return
            
            result = self.rates_updater.run_update()
            
            if result.get('status') == 'success':
                print("Rates update completed successfully!")
                print(f"Fetched: {result['total_rates_fetched']} rates")
                print(f"Saved: {result['rates_saved']} rates")
                print(f"Crypto: {result['crypto_rates']}, Fiat: {result['fiat_rates']}")
                print(f"Time: {result['execution_time_seconds']}s")
                
                # Показываем несколько примеров обновленных курсов
                rates = self.rates_storage.get_all_rates()
                if rates:
                    sample_pairs = list(rates.keys())[:5]
                    print("\nSample updated rates:")
                    for pair in sample_pairs:
                        rate_data = rates[pair]
                        print(f"   {pair}: {rate_data.get('rate'):.6f} ({rate_data.get('source')})")
            else:
                print("Rates update failed")
                
        except Exception as e:
            print(f"Error updating rates: {str(e)}")
    
    def handle_show_rates(self, args):
        """Обработка команды показа курсов"""
        try:
            rates = self.rates_storage.get_all_rates()
            
            if not rates:
                print("No exchange rates available")
                print("Use 'update-rates' to fetch rates")
                return
            
            # Фильтрация если указана валюта
            filtered_rates = {}
            if args.currency:
                target_currency = args.currency.upper()
                for pair, rate_data in rates.items():
                    if target_currency in pair:
                        filtered_rates[pair] = rate_data
            else:
                filtered_rates = rates
            
            if not filtered_rates:
                print(f"No rates found for currency: {args.currency}")
                return
            
            # Сортировка
            sorted_pairs = sorted(filtered_rates.items())
            
            # Применяем лимит если задан --top
            if args.top and args.top > 0:
                # Сортируем по значению курса (для USD пар)
                usd_pairs = [(pair, data) for pair, data in sorted_pairs if pair.endswith('_USD')]
                usd_pairs.sort(key=lambda x: x[1].get('rate', 0), reverse=True)
                sorted_pairs = usd_pairs[:args.top]
            
            # Форматируем вывод
            table = PrettyTable()
            table.field_names = ["Pair", "Rate", "Updated", "Source"]
            table.align["Pair"] = "l"
            table.align["Rate"] = "r"
            table.align["Updated"] = "l"
            table.align["Source"] = "l"
            
            for pair, rate_data in sorted_pairs:
                rate = rate_data.get('rate', 0)
                updated = rate_data.get('updated_at', 'Unknown')
                source = rate_data.get('source', 'Unknown')
                
                # Форматируем время
                if updated != 'Unknown':
                    try:
                        dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        updated = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                table.add_row([pair, f"{rate:.6f}", updated, source])
            
            total_rates = self.rates_storage.get_stats()['current_rates_count']
            print(f"Exchange Rates (showing {len(sorted_pairs)} of {total_rates}):")
            print(table)
            
            # Информация о свежести
            freshness_check = RatesUseCases.check_rates_freshness()
            if freshness_check[0]:
                print(f"{freshness_check[1]}")
            else:
                print(f"{freshness_check[1]}")
                print("   Use 'update-rates' to refresh")
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def handle_parser_status(self, args):
        """Обработка команды статуса парсера"""
        try:
            # Статус обновлений
            updater_status = self.rates_updater.get_status()
            freshness = self.rates_updater.check_freshness()
            
            # Статистика хранилища
            storage_stats = self.rates_storage.get_stats()
            
            print("Parser Service Status:")
            print("=" * 50)
            
            print("Update Status:")
            print(f"Last update: {updater_status['last_update_time'] or 'Never'}")
            print(f"Update count: {updater_status['update_count']}")
            print(f"Successful: {updater_status['successful_updates']}")
            print(f"Failed: {updater_status['failed_updates']}")
            print(f"Clients: {', '.join(updater_status['clients'])}")
            
            print("\nFreshness Check:")
            print(f"Status: {'Fresh' if freshness['is_fresh'] else 'Outdated'}")
            print(f"Message: {freshness['message']}")
            print(f"TTL: {freshness['ttl_seconds']}s")
            
            print("\nStorage Stats:")
            print(f"Current rates: {storage_stats['current_rates_count']}")
            print(f"Crypto pairs: {storage_stats['crypto_pairs_count']}")
            print(f"Fiat pairs: {storage_stats['fiat_pairs_count']}")
            print(f"File size: {storage_stats['rates_file_size_kb']} KB")
            print(f"Last refresh: {storage_stats['last_refresh']}")
            
            print("\nConfiguration:")
            print(f"Update interval: {self.parser_config.UPDATE_INTERVAL}s")
            print(f"Rates TTL: {self.parser_config.RATES_TTL}s")
            print(f"Request timeout: {self.parser_config.REQUEST_TIMEOUT}s")
            
            # Проверка API ключей
            print("\nAPI Keys:")
            print(f"ExchangeRate-API: {'Set' if self.parser_config.EXCHANGERATE_API_KEY else 'Not set'}")
            print(f"CoinGecko: {'Set' if self.parser_config.COINGECKO_API_KEY else 'Not set'}")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # ==================== СЛУЖЕБНЫЕ КОМАНДЫ ====================
    
    def handle_db_stats(self, args):
        """Обработка команды статистики базы данных"""
        try:
            stats = self.db.get_database_stats()
            
            print("Database Statistics:")
            print("=" * 50)
            
            print(f"Users: {stats['users']}")
            print(f"Portfolios: {stats['portfolios']}")
            print(f"Exchange rates: {stats['exchange_rates']}")
            print(f"Transactions: {stats['transactions']}")
            print(f"Total size: {stats['total_size_kb']:.2f} KB")
            print(f"Last rates update: {stats['last_rates_update']}")
            
            print(f"\nData directory: {self.db.data_dir.absolute()}")
            
            # Показываем файлы
            print("\nFiles:")
            for file in self.db.data_dir.glob("*.json"):
                size_kb = file.stat().st_size / 1024
                print(f"{file.name}: {size_kb:.2f} KB")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def handle_help(self, args):
        """Обработка команды помощи"""
        self._print_help()
    
    def _print_help(self):
        """Выводит справку по командам"""
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                  VALUTATRADE HUB - HELP                      ║
╚══════════════════════════════════════════════════════════════╝

USER MANAGEMENT:
  register --username USERNAME --password PASSWORD
    Register a new user
  
  login --username USERNAME --password PASSWORD
    Login to the system
  
  logout
    Logout from the system
  
  status
    Show current session status

PORTFOLIO OPERATIONS:
  show-portfolio [--base CURRENCY]
    Show your portfolio (default base: USD)
  
  buy --currency CURRENCY --amount AMOUNT
    Buy currency (e.g., buy --currency EUR --amount 100)
  
  sell --currency CURRENCY --amount AMOUNT
    Sell currency (e.g., sell --currency BTC --amount 0.5)

CURRENCY INFORMATION:
  list-currencies
    List all available currencies
  
  currency-info --currency CURRENCY
    Get detailed information about a currency
  
  get-rate --from CURRENCY --to CURRENCY
    Get exchange rate (e.g., get-rate --from USD --to EUR)

PARSER SERVICE:
  update-rates [--source coingecko|exchangerate|mock]
    Update exchange rates from APIs
  
  show-rates [--currency CURRENCY] [--top N]
    Show exchange rates with filters
  
  parser-status
    Show parser service status

SYSTEM COMMANDS:
  db-stats
    Show database statistics
  
  help
    Show this help message

EXAMPLES:
  poetry run valutatrade register --username alice --password 1234
  poetry run valutatrade login --username alice --password 1234
  poetry run valutatrade buy --currency EUR --amount 100
  poetry run valutatrade show-portfolio --base USD
  poetry run valutatrade update-rates
  poetry run valutatrade show-rates --top 5

Data is stored in: {data_dir}
Logs are stored in: {log_dir}
        """.format(
            data_dir=self.data_dir,
            log_dir=self.settings.get('log_dir', 'logs')
        )
        
        print(help_text)
    
    # ==================== ОСНОВНОЙ МЕТОД ====================
    
    def run(self):
        """Основной метод запуска CLI"""
        parser = argparse.ArgumentParser(
            description='ValutaTrade Hub - Currency Trading Platform',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._print_help()
        )
        
        subparsers = parser.add_subparsers(
            dest='command',
            title='Available Commands',
            metavar='COMMAND'
        )
        
        # Регистрируем все команды
        self._register_commands(subparsers)
        
        # Парсим аргументы
        args = parser.parse_args()
        
        # Если команда не указана, показываем help
        if not args.command:
            self._print_help()
            return
        
        # Выполняем команду
        try:
            self._execute_command(args)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            sys.exit(0)
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            logger.error(f"CLI error: {e}", exc_info=True)
            sys.exit(1)
    
    def _register_commands(self, subparsers):
        """Регистрирует все команды CLI"""
        
        # register
        register_parser = subparsers.add_parser('register', help='Register new user')
        register_parser.add_argument('--username', required=True, help='Username')
        register_parser.add_argument('--password', required=True, help='Password')
        register_parser.set_defaults(handler=self.handle_register)
        
        # login
        login_parser = subparsers.add_parser('login', help='Login to system')
        login_parser.add_argument('--username', required=True, help='Username')
        login_parser.add_argument('--password', required=True, help='Password')
        login_parser.set_defaults(handler=self.handle_login)
        
        # logout
        logout_parser = subparsers.add_parser('logout', help='Logout from system')
        logout_parser.set_defaults(handler=self.handle_logout)
        
        # status
        status_parser = subparsers.add_parser('status', help='Show session status')
        status_parser.set_defaults(handler=self.handle_status)
        
        # show-portfolio
        portfolio_parser = subparsers.add_parser('show-portfolio', help='Show portfolio')
        portfolio_parser.add_argument('--base', default='USD', help='Base currency (default: USD)')
        portfolio_parser.set_defaults(handler=self.handle_show_portfolio)
        
        # buy
        buy_parser = subparsers.add_parser('buy', help='Buy currency')
        buy_parser.add_argument('--currency', required=True, help='Currency code (e.g., EUR)')
        buy_parser.add_argument('--amount', type=float, required=True, help='Amount to buy')
        buy_parser.set_defaults(handler=self.handle_buy)
        
        # sell
        sell_parser = subparsers.add_parser('sell', help='Sell currency')
        sell_parser.add_argument('--currency', required=True, help='Currency code')
        sell_parser.add_argument('--amount', type=float, required=True, help='Amount to sell')
        sell_parser.set_defaults(handler=self.handle_sell)
        
        # get-rate
        rate_parser = subparsers.add_parser('get-rate', help='Get exchange rate')
        rate_parser.add_argument('--from', required=True, dest='from_currency', help='From currency')
        rate_parser.add_argument('--to', required=True, help='To currency')
        rate_parser.set_defaults(handler=self.handle_get_rate)
        
        # list-currencies
        currencies_parser = subparsers.add_parser('list-currencies', help='List available currencies')
        currencies_parser.set_defaults(handler=self.handle_list_currencies)
        
        # currency-info
        info_parser = subparsers.add_parser('currency-info', help='Get currency information')
        info_parser.add_argument('--currency', required=True, help='Currency code')
        info_parser.set_defaults(handler=self.handle_currency_info)
        
        # update-rates
        update_parser = subparsers.add_parser('update-rates', help='Update exchange rates')
        update_parser.add_argument('--source', choices=['coingecko', 'exchangerate', 'mock'],
                                  help='API source (default: all available)')
        update_parser.set_defaults(handler=self.handle_update_rates)
        
        # show-rates
        show_rates_parser = subparsers.add_parser('show-rates', help='Show exchange rates')
        show_rates_parser.add_argument('--currency', help='Filter by currency')
        show_rates_parser.add_argument('--top', type=int, help='Show top N rates by value')
        show_rates_parser.set_defaults(handler=self.handle_show_rates)
        
        # parser-status
        parser_status_parser = subparsers.add_parser('parser-status', help='Show parser service status')
        parser_status_parser.set_defaults(handler=self.handle_parser_status)
        
        # db-stats
        db_stats_parser = subparsers.add_parser('db-stats', help='Show database statistics')
        db_stats_parser.set_defaults(handler=self.handle_db_stats)
        
        # help
        help_parser = subparsers.add_parser('help', help='Show help message')
        help_parser.set_defaults(handler=self.handle_help)
    
    def _execute_command(self, args):
        """Выполняет команду на основе переданных аргументов"""
        if hasattr(args, 'handler'):
            args.handler(args)
        else:
            print(f"Unknown command: {args.command}")
            print("Use 'help' to see available commands")


def main():
    """Точка входа в приложение"""
    try:
        cli = CLIInterface()
        cli.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()