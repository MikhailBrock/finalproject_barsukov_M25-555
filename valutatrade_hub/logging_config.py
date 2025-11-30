import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Настройка системы логирования"""
    # Создаем папку для логов
    os.makedirs('logs', exist_ok=True)
    
    # Настраиваем основной логгер
    logger = logging.getLogger('valutatrade')
    logger.setLevel(logging.INFO)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        'logs/valutatrade.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
