"""
Командный интерфейс (CLI) приложения
"""

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from prettytable import PrettyTable

from ..core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    UserNotFoundError,
)
from ..core.usecases import UseCases
from ..infra.database import DatabaseManager
from ..parser_service.updater import RatesUpdater


class CLI:
    """Командный интерфейс приложения"""

    def __init__(self):
        self.usecases = UseCases()
        self.db = DatabaseManager()
        self.session_file = Path(".valutatrade_session.json")
        self._load_session()

    def _load_session(self):
        """Загружает сессию из файла"""
        try:
            if self.session_file.exists():
                with open(self.session_file, "r", encoding="utf-8") as f:
                    session = json.load(f)
                    self.current_user = session.get("user_id")
            else:
                self.current_user = None
        except (json.JSONDecodeError, IOError):
            self.current_user = None

    def _save_session(self):
        """Сохраняет сессию в файл"""
        try:
            session_data = {"user_id": self.current_user}
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
        except IOError:
            pass

    def _clear_session(self):
        """Очищает сессию"""
        try:
            if self.session_file.exists():
                os.remove(self.session_file)
        except OSError:
            pass

    def ensure_logged_in(self):
        """Проверяет, что пользователь вошел в систему"""
        if not self.current_user:
            print("Сначала выполните login")
            sys.exit(1)

    def register(self, args):
        """Регистрирует нового пользователя"""
        try:
            password = args.password
            if not password:
                password = getpass.getpass("Введите пароль: ")

            user = self.usecases.register_user(args.username, password)
            print(
                f"Пользователь '{user.username}' зарегистрирован (id={user.user_id})."
            )
            print("Войдите: login --username", user.username)

        except ValueError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

    def login(self, args):
        """Вход в систему"""
        try:
            password = args.password
            if not password:
                password = getpass.getpass("Введите пароль: ")

            user = self.usecases.login_user(args.username, password)
            self.current_user = user.user_id
            self._save_session()
            print(f"Вы вошли как '{user.username}'")

        except UserNotFoundError:
            print(f"Пользователь '{args.username}' не найден")
            sys.exit(1)
        except AuthenticationError:
            print("Неверный пароль")
            sys.exit(1)

    def logout(self, args):
        """Выход из системы"""
        self.current_user = None
        self._clear_session()
        print("Вы вышли из системы")

    def show_portfolio(self, args):
        """Показывает портфель пользователя"""
        self.ensure_logged_in()

        try:
            base_currency = getattr(args, "base", None) or "USD"
            portfolio_info = self.usecases.get_user_portfolio(
                self.current_user, base_currency
            )

            print(
                f"\nПортфель пользователя '{portfolio_info['username']}' "
                f"(база: {portfolio_info['base_currency']}):"
            )
            print("-" * 50)

            table = PrettyTable()
            table.field_names = [
                "Валюта",
                "Баланс",
                f"Стоимость ({portfolio_info['base_currency']})",
            ]
            table.align["Валюта"] = "l"
            table.align["Баланс"] = "r"
            table.align[f"Стоимость ({portfolio_info['base_currency']})"] = "r"

            total = 0
            for wallet in portfolio_info["wallets"]:
                if wallet["currency_code"] in ["BTC", "ETH"]:
                    balance_str = f"{wallet['balance']:.4f}"
                else:
                    balance_str = f"{wallet['balance']:.2f}"
                value_str = f"{wallet['value_in_base']:.2f}"
                table.add_row([wallet["currency_code"], balance_str, value_str])
                total += wallet["value_in_base"]

            print(table)
            print("-" * 50)
            print(f"ИТОГО: {total:,.2f} {portfolio_info['base_currency']}\n")

        except ValueError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

    def buy(self, args):
        """Покупает валюту"""
        self.ensure_logged_in()

        try:
            result = self.usecases.buy_currency(
                self.current_user, args.currency, args.amount
            )

            print(f"\nПокупка выполнена: {args.amount:.4f} {args.currency}")

            if result["rate"]:
                print(f"По курсу: {result['rate']:.2f} USD/{args.currency}")
                if result["estimated_cost_usd"]:
                    print(
                        f"Оценочная стоимость покупки: "
                        f"{result['estimated_cost_usd']:,.2f} USD"
                    )

            print(f"Новый баланс {args.currency}: {result['new_balance']:.4f}\n")

        except ValueError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

    def sell(self, args):
        """Продает валюту"""
        self.ensure_logged_in()

        try:
            result = self.usecases.sell_currency(
                self.current_user, args.currency, args.amount
            )

            print(f"\nПродажа выполнена: {args.amount:.4f} {args.currency}")

            if result["rate"]:
                print(f"По курсу: {result['rate']:.2f} USD/{args.currency}")
                if result["estimated_revenue_usd"]:
                    print(
                        f"Оценочная выручка: "
                        f"{result['estimated_revenue_usd']:,.2f} USD"
                    )

            print(
                f"Баланс {args.currency}: было {result['old_balance']:.4f} "
                f"→ стало {result['new_balance']:.4f}\n"
            )

        except ValueError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

    def get_rate(self, args):
        """Получает курс валюты"""
        try:
            rate_info = self.usecases.get_exchange_rate(args.frm, args.to)

            print(
                f"\nКурс {rate_info['from']}→{rate_info['to']}: "
                f"{rate_info['rate']:.6f}"
            )
            print(f"Обновлено: {rate_info['updated_at']}")
            print(f"Источник: {rate_info['source']}")

            if rate_info["rate"] != 0:
                reverse_rate = 1.0 / rate_info["rate"]
                print(
                    f"Обратный курс {rate_info['to']}→{rate_info['from']}: "
                    f"{reverse_rate:.6f}"
                )
            print()

        except (CurrencyNotFoundError, ApiRequestError) as e:
            print(f"Ошибка: {e}")
            print(
                "Рекомендация: выполните команду 'update-rates' "
                "для обновления курсов"
            )
            sys.exit(1)

    def update_rates(self, args):
        """Обновляет курсы валют"""
        print("Запуск обновления курсов...")

        try:
            # source = getattr(args, "source", "all")
            updater = RatesUpdater()
            result = updater.run_update()

            print("\nОбновление завершено успешно!")
            print(f"Обновлено пар: {result['total_rates']}")
            print(f"Последнее обновление: {result['last_refresh']}")
            print("Файл: data/rates.json\n")

        except Exception as e:
            print(f"Ошибка при обновлении курсов: {e}")
            sys.exit(1)

    def show_rates(self, args):
        """Показывает курсы валют"""
        try:
            rates = self.db.load_rates()
            pairs = rates.get("pairs", {})
            last_refresh = rates.get("last_refresh", "неизвестно")

            if not pairs:
                print("Локальный кеш курсов пуст.")
                print("Выполните 'update-rates', чтобы загрузить данные.")
                return

            print(f"\nКурсы из кэша (обновлено: {last_refresh}):")
            print("-" * 50)

            table = PrettyTable()
            table.field_names = ["Пара", "Курс", "Обновлено", "Источник"]
            table.align["Пара"] = "l"
            table.align["Курс"] = "r"

            filtered_pairs = []

            currency = getattr(args, "currency", None)
            if currency:
                currency = currency.upper()
                for pair_name, data in pairs.items():
                    if currency in pair_name:
                        filtered_pairs.append((pair_name, data))
            else:
                filtered_pairs = list(pairs.items())

            top = getattr(args, "top", None)
            if top:
                sorted_pairs = sorted(
                    filtered_pairs, key=lambda x: x[1]["rate"], reverse=True
                )
                filtered_pairs = sorted_pairs[:top]
            else:
                filtered_pairs.sort(key=lambda x: x[0])

            for pair_name, data in filtered_pairs:
                rate = data["rate"]
                updated = data["updated_at"]
                source = data.get("source", "unknown")

                if rate < 0.01:
                    rate_str = f"{rate:.8f}"
                elif rate < 1:
                    rate_str = f"{rate:.6f}"
                elif rate < 1000:
                    rate_str = f"{rate:.4f}"
                else:
                    rate_str = f"{rate:,.2f}"

                table.add_row([pair_name, rate_str, updated, source])

            print(table)
            print()

        except Exception as e:
            print(f"Ошибка: {e}")
            sys.exit(1)


def main():
    """Основная функция CLI"""
    cli = CLI()

    parser = argparse.ArgumentParser(
        description="ValutaTrade Hub - платформа для торговли валютами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  register --username alice --password 1234
  login --username alice --password 1234
  logout
  show-portfolio --base USD
  buy --currency BTC --amount 0.05
  sell --currency BTC --amount 0.01
  get-rate --from USD --to BTC
  update-rates
  show-rates --top 5
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    register_parser = subparsers.add_parser(
        "register", help="Регистрация нового пользователя"
    )
    register_parser.add_argument("--username", required=True, help="Имя пользователя")
    register_parser.add_argument(
        "--password", help="Пароль (можно ввести интерактивно)"
    )
    register_parser.set_defaults(func=cli.register)

    login_parser = subparsers.add_parser("login", help="Вход в систему")
    login_parser.add_argument("--username", required=True, help="Имя пользователя")
    login_parser.add_argument("--password", help="Пароль (можно ввести интерактивно)")
    login_parser.set_defaults(func=cli.login)

    logout_parser = subparsers.add_parser("logout", help="Выход из системы")
    logout_parser.set_defaults(func=cli.logout)

    portfolio_parser = subparsers.add_parser("show-portfolio", help="Показать портфель")
    portfolio_parser.add_argument("--base", help="Базовая валюта (по умолчанию: USD)")
    portfolio_parser.set_defaults(func=cli.show_portfolio)

    buy_parser = subparsers.add_parser("buy", help="Купить валюту")
    buy_parser.add_argument(
        "--currency", required=True, help="Код покупаемой валюты (например, BTC)"
    )
    buy_parser.add_argument(
        "--amount", type=float, required=True, help="Количество покупаемой валюты"
    )
    buy_parser.set_defaults(func=cli.buy)

    sell_parser = subparsers.add_parser("sell", help="Продать валюту")
    sell_parser.add_argument("--currency", required=True, help="Код продаваемой валюты")
    sell_parser.add_argument(
        "--amount", type=float, required=True, help="Количество продаваемой валюты"
    )
    sell_parser.set_defaults(func=cli.sell)

    rate_parser = subparsers.add_parser("get-rate", help="Получить курс валюты")
    rate_parser.add_argument(
        "--from", dest="frm", required=True, help="Исходная валюта"
    )
    rate_parser.add_argument("--to", required=True, help="Целевая валюта")
    rate_parser.set_defaults(func=cli.get_rate)

    update_parser = subparsers.add_parser("update-rates", help="Обновить курсы валют")
    update_parser.add_argument(
        "--source",
        choices=["coingecko", "exchangerate", "all"],
        default="all",
        help="Источник данных",
    )
    update_parser.set_defaults(func=cli.update_rates)

    show_rates_parser = subparsers.add_parser("show-rates", help="Показать курсы валют")
    show_rates_parser.add_argument(
        "--currency", help="Показать курс только для указанной валюты"
    )
    show_rates_parser.add_argument(
        "--top", type=int, help="Показать N самых дорогих криптовалют"
    )
    show_rates_parser.add_argument(
        "--base", help="Показать все курсы относительно указанной базы"
    )
    show_rates_parser.set_defaults(func=cli.show_rates)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nОперация прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
