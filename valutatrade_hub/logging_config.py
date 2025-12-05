"""
Настройка логирования
"""

import logging
import logging.handlers

from .infra.settings import SettingsLoader


def setup_logging():
    """Настраивает логирование"""
    settings = SettingsLoader()

    # Создаем директорию для логов
    log_file = settings.log_file
    log_file.parent.mkdir(exist_ok=True)

    # Настраиваем формат
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Файловый обработчик с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Удаляем существующие обработчики
    root_logger.handlers.clear()

    # Добавляем обработчики
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


# Инициализируем логирование при импорте
logger = setup_logging()
