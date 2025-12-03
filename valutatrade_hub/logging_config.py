import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    """
    Настройка системы логирования для всего приложения.
    Создает логгеры для разных компонентов с разными уровнями.
    """
    settings = SettingsLoader()
    
    # Создаем директории для логов
    log_dir = Path(settings.get('log_dir', 'logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Базовые настройки
    log_level_name = settings.get('log_level', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    log_format = settings.get('log_format', 
                             '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    date_format = settings.get('log_date_format', '%Y-%m-%d %H:%M:%S')
    
    max_size_mb = settings.get('log_max_size_mb', 10)
    backup_count = settings.get('log_backup_count', 5)
    
    # Форматтер
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # ==================== ОСНОВНОЙ ЛОГГЕР ====================
    main_logger = logging.getLogger('valutatrade')
    main_logger.setLevel(log_level)
    main_logger.propagate = False  # Предотвращаем дублирование
    
    # Файловый обработчик с ротацией по размеру
    main_log_file = log_dir / settings.get('log_file', 'valutatrade.log')
    file_handler = RotatingFileHandler(
        main_log_file,
        maxBytes=max_size_mb * 1024 * 1024,  # Конвертируем в байты
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Добавляем обработчики к основному логгеру
    main_logger.addHandler(file_handler)
    main_logger.addHandler(console_handler)
    
    # ==================== ЛОГГЕР ДЕЙСТВИЙ ====================
    actions_logger = logging.getLogger('valutatrade.actions')
    actions_logger.setLevel(logging.INFO)
    actions_logger.propagate = False
    
    # Отдельный файл для действий
    actions_log_file = log_dir / 'actions.log'
    actions_handler = TimedRotatingFileHandler(
        actions_log_file,
        when='midnight',  # Ротация каждый день
        interval=1,
        backupCount=7,  # Храним 7 дней
        encoding='utf-8'
    )
    actions_handler.setFormatter(formatter)
    actions_logger.addHandler(actions_handler)
    
    # ==================== ЛОГГЕР БАЗЫ ДАННЫХ ====================
    db_logger = logging.getLogger('valutatrade.database')
    db_logger.setLevel(logging.DEBUG)
    db_logger.propagate = False
    
    db_log_file = log_dir / 'database.log'
    db_handler = RotatingFileHandler(
        db_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    db_handler.setFormatter(formatter)
    db_logger.addHandler(db_handler)
    
    # ==================== ЛОГГЕР API ====================
    api_logger = logging.getLogger('valutatrade.api')
    api_logger.setLevel(logging.DEBUG)
    api_logger.propagate = False
    
    api_log_file = log_dir / 'api.log'
    api_handler = RotatingFileHandler(
        api_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    api_handler.setFormatter(formatter)
    api_logger.addHandler(api_handler)
    
    # ==================== ЛОГГЕР ПАРСЕРА ====================
    parser_logger = logging.getLogger('valutatrade.parser')
    parser_logger.setLevel(logging.INFO)
    parser_logger.propagate = False
    
    parser_log_file = log_dir / 'parser.log'
    parser_handler = TimedRotatingFileHandler(
        parser_log_file,
        when='H',  # Ротация каждый час
        interval=1,
        backupCount=24,  # Храним 24 часа
        encoding='utf-8'
    )
    parser_handler.setFormatter(formatter)
    parser_logger.addHandler(parser_handler)
    
    # ==================== НАСТРОЙКА ДРУГИХ ЛОГГЕРОВ ====================
    
    # Логгер CLI
    cli_logger = logging.getLogger('valutatrade.cli')
    cli_logger.setLevel(log_level)
    
    # Логгер бизнес-логики
    usecases_logger = logging.getLogger('valutatrade.usecases')
    usecases_logger.setLevel(log_level)
    
    # Логгер моделей
    models_logger = logging.getLogger('valutatrade.models')
    models_logger.setLevel(logging.WARNING)  # Только предупреждения и ошибки
    
    # ==================== JSON ФОРМАТТЕР (опционально) ====================
    
    # Включаем JSON логирование если нужно
    if settings.get('json_logging', False):
        try:
            import json
            from pythonjsonlogger import jsonlogger
            
            class JSONFormatter(jsonlogger.JsonFormatter):
                def add_fields(self, log_record, record, message_dict):
                    super().add_fields(log_record, record, message_dict)
                    log_record['timestamp'] = record.created
                    log_record['level'] = record.levelname
                    log_record['logger'] = record.name
            
            json_formatter = JSONFormatter(
                '%(timestamp)s %(level)s %(logger)s %(message)s'
            )
            
            json_log_file = log_dir / 'valutatrade.json.log'
            json_handler = RotatingFileHandler(
                json_log_file,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            json_handler.setFormatter(json_formatter)
            main_logger.addHandler(json_handler)
            
        except ImportError:
            main_logger.warning("python-json-logger not installed. JSON logging disabled.")
    
    # ==================== ВЫВОД ИНФОРМАЦИИ ====================
    
    main_logger.info("=" * 60)
    main_logger.info("LOGGING SYSTEM INITIALIZED")
    main_logger.info(f"Log level: {log_level_name}")
    main_logger.info(f"Log directory: {log_dir.absolute()}")
    main_logger.info(f"Main log file: {main_log_file.absolute()}")
    main_logger.info("=" * 60)
    
    print(f"Логирование настроено. Уровень: {log_level_name}")
    print(f"Логи сохраняются в: {log_dir.absolute()}")
    
    return main_logger


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер по имени с автоматической настройкой.
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    # Если логгер еще не настроен, настраиваем
    if not logging.getLogger('valutatrade').handlers:
        setup_logging()
    
    return logging.getLogger(name)


class LoggingMixin:
    """Миксин для добавления логирования в классы"""
    
    @property
    def logger(self) -> logging.Logger:
        """Возвращает логгер для текущего класса"""
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__name__
            self._logger = get_logger(f'valutatrade.{class_name}')
        return self._logger
    
    def log_debug(self, message: str, **kwargs):
        """Логирует отладочное сообщение"""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.debug(message)
    
    def log_info(self, message: str, **kwargs):
        """Логирует информационное сообщение"""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.info(message)
    
    def log_warning(self, message: str, **kwargs):
        """Логирует предупреждение"""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.warning(message)
    
    def log_error(self, message: str, **kwargs):
        """Логирует ошибку"""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.error(message)
    
    def log_exception(self, message: str, exception: Exception):
        """Логирует исключение с трассировкой"""
        self.logger.error(f"{message}: {exception}", exc_info=True)


def log_function_call(log_args: bool = True, log_result: bool = False):
    """
    Декоратор для логирования вызовов функций.
    
    Args:
        log_args: Логировать аргументы функции
        log_result: Логировать результат функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(f'valutatrade.{func.__module__}.{func.__name__}')
            
            # Логируем вызов
            call_info = f"Calling {func.__name__}"
            if log_args:
                args_str = ', '.join(str(arg) for arg in args[1:] if args)  # Пропускаем self
                kwargs_str = ', '.join(f"{k}={v}" for k, v in kwargs.items())
                all_args = ', '.join(filter(None, [args_str, kwargs_str]))
                if all_args:
                    call_info += f" with args: {all_args}"
            
            logger.debug(call_info)
            
            # Выполняем функцию
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Логируем результат если нужно
                if log_result:
                    result_str = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                    logger.debug(f"{func.__name__} returned: {result_str} "
                                f"(took {execution_time:.3f}s)")
                else:
                    logger.debug(f"{func.__name__} completed in {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
                raise
        
        return wrapper
    return decorator


def cleanup_old_logs(days_to_keep: int = 30):
    """
    Очищает старые логи файлы.
    
    Args:
        days_to_keep: Количество дней для хранения логов
    """
    import time
    from pathlib import Path
    
    settings = SettingsLoader()
    log_dir = Path(settings.get('log_dir', 'logs'))
    
    if not log_dir.exists():
        return
    
    now = time.time()
    cutoff = now - (days_to_keep * 24 * 60 * 60)
    
    deleted_count = 0
    for log_file in log_dir.glob("*.log*"):  * Включаем rotated файлы
        if log_file.is_file():
            file_mtime = log_file.stat().st_mtime
            if file_mtime < cutoff:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    get_logger('valutatrade.logging').error(
                        f"Failed to delete old log file {log_file}: {e}"
                    )
    
    if deleted_count > 0:
        get_logger('valutatrade.logging').info(
            f"Cleaned up {deleted_count} old log files (older than {days_to_keep} days)"
        )


# Импорт необходимых модулей для декораторов
import functools
import time
import json