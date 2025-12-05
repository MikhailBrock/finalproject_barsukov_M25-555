#!/usr/bin/env python3
"""
Скрипт для записи asciinema демо
Выполняет реальные команды через subprocess
"""

import os
import shutil
import subprocess
import time


def print_step(step, description):
    """Выводит шаг демо"""
    print(f"\n\033[1;36m{'='*60}\033[0m")
    print(f"\033[1;32mШаг {step}: {description}\033[0m")
    print(f"\033[1;36m{'='*60}\033[0m\n")
    time.sleep(0.5)


def run_command(command, delay=1.5):
    """Выполняет команду и выводит результат"""
    print(f"\033[1;33m$\033[0m \033[1;37m{command}\033[0m")
    time.sleep(0.3)

    # Выполняем команду
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Выводим результат
    if result.stdout:
        print(f"\033[0;37m{result.stdout}\033[0m")

    if result.stderr and "INFO" not in result.stderr and "DEBUG" not in result.stderr:
        print(f"\033[0;31m{result.stderr}\033[0m")

    time.sleep(delay)
    return result.returncode


def cleanup():
    """Очищает данные для чистого демо"""
    print("Очистка данных для демо...")

    # Удаляем старые данные
    for path in ["data", "logs", ".valutatrade_session.json"]:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    # Создаем структуру
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Инициализируем пустые файлы
    with open("data/users.json", "w") as f:
        f.write('{"users": [], "last_user_id": 0}')
    with open("data/portfolios.json", "w") as f:
        f.write('{"portfolios": []}')
    with open("data/rates.json", "w") as f:
        f.write('{"pairs": {}, "last_refresh": null}')
    with open("data/exchange_rates.json", "w") as f:
        f.write('{"history": [], "last_updated": null}')

    print("Данные очищены ✓")
    time.sleep(1)


def main():
    """Основная функция демо"""

    print("\033[1;35m" + "=" * 60 + "\033[0m")
    print("\033[1;35m    ДЕМОНСТРАЦИЯ VALUTATRADE HUB    \033[0m")
    print("\033[1;35m" + "=" * 60 + "\033[0m\n")

    time.sleep(1)

    # Очистка данных
    cleanup()

    # ============ ОСНОВНЫЕ КОМАНДЫ ============

    # 1. Регистрация
    print_step(1, "Регистрация нового пользователя")
    run_command(
        "poetry run python3 main.py register --username demo_user --password demo123"
    )

    # 2. Вход в систему
    print_step(2, "Вход в систему")
    run_command(
        "poetry run python3 main.py login --username demo_user --password demo123"
    )

    # 3. Обновление курсов
    print_step(3, "Обновление курсов валют")
    run_command("poetry run python3 main.py update-rates")

    # 4. Просмотр курсов
    print_step(4, "Просмотр топ-5 курсов")
    run_command("poetry run python3 main.py show-rates --top 5")

    # 5. Получение конкретного курса
    print_step(5, "Получение курса USD → BTC")
    run_command("poetry run python3 main.py get-rate --from USD --to BTC")

    # 6. Покупка валюты
    print_step(6, "Покупка 0.05 BTC")
    run_command("poetry run python3 main.py buy --currency BTC --amount 0.05")

    # 7. Просмотр портфеля
    print_step(7, "Просмотр портфеля пользователя")
    run_command("poetry run python3 main.py show-portfolio --base USD")

    # 8. Продажа валюты
    print_step(8, "Продажа 0.01 BTC")
    run_command("poetry run python3 main.py sell --currency BTC --amount 0.01")

    # 9. Портфель после продажи
    print_step(9, "Портфель после продажи")
    run_command("poetry run python3 main.py show-portfolio")

    # ============ ДЕМОНСТРАЦИЯ ОШИБОК ============

    print("\033[1;31m" + "=" * 60 + "\033[0m")
    print("\033[1;31m    ДЕМОНСТРАЦИЯ ОБРАБОТКИ ОШИБОК    \033[0m")
    print("\033[1;31m" + "=" * 60 + "\033[0m\n")
    time.sleep(1)

    # 10. Попытка продажи больше чем есть
    print("\n\033[1;31m10. Попытка продажи больше чем есть:\033[0m")
    run_command(
        "poetry run python3 main.py sell --currency BTC --amount 100.0", delay=2
    )

    # 11. Попытка покупки неизвестной валюты
    print("\n\033[1;31m11. Попытка покупки неизвестной валюты:\033[0m")
    run_command("poetry run python3 main.py buy --currency XYZ --amount 1.0", delay=2)

    # 12. Попытка доступа без входа (выход и попытка)
    print("\n\033[1;31m12. Выход и попытка доступа:\033[0m")
    run_command("poetry run python3 main.py logout")
    run_command("poetry run python3 main.py show-portfolio", delay=2)

    # 13. Попытка входа с неверным паролем
    print("\n\033[1;31m13. Попытка входа с неверным паролем:\033[0m")
    run_command(
        "poetry run python3 main.py login --username demo_user --password wrongpass",
        delay=2,
    )

    # 14. Восстановление сессии
    print("\n\033[1;32m14. Восстановление сессии:\033[0m")
    run_command(
        "poetry run python3 main.py login --username demo_user --password demo123"
    )
    run_command("poetry run python3 main.py show-portfolio")

    # ============ ЗАВЕРШЕНИЕ ============

    print("\033[1;35m" + "=" * 60 + "\033[0m")
    print("\033[1;35m    ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!    \033[0m")
    print("\033[1;35m" + "=" * 60 + "\033[0m\n")


if __name__ == "__main__":
    main()
