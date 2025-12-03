#!/usr/bin/env python3
"""
ValutaTrade Hub - Currency Trading Simulation Platform

Main entry point for the application.
This module provides the main() function which serves as the entry point
for the console application.

Usage:
    poetry run valutatrade --help
    poetry run valutatrade register --username test --password test
    poetry run valutatrade login --username test --password test
    poetry run valutatrade show-portfolio

Author: Barsukov Mikhail Alekseevich
Version: 1.0.0
"""

import sys
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

from valutatrade_hub.cli.interface import main as cli_main


def main():
    """
    Основная функция запуска приложения.
    Обрабатывает аргументы командной строки и запускает соответствующий функционал.
    
    Returns:
        Код возврата (0 - успех, 1 - ошибка)
    """
    try:
        # Проверяем наличие необходимых директорий
        data_dir = Path("data")
        logs_dir = Path("logs")
        
        if not data_dir.exists():
            data_dir.mkdir(parents=True)
            print(f"Created data directory: {data_dir.absolute()}")
        
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True)
            print(f"Created logs directory: {logs_dir.absolute()}")
        
        # Запускаем CLI интерфейс
        cli_main()
        
    except KeyboardInterrupt:
        print("\n\nApplication terminated by user")
        return 0
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())