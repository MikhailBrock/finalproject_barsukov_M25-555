import time
import threading
import logging
import schedule
from datetime import datetime
from typing import Optional, Callable

from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater
from valutatrade_hub.parser_service.storage import RatesStorage


logger = logging.getLogger('valutatrade.parser.scheduler')


class ParserScheduler:
    """
    Планировщик для периодического обновления курсов валют.
    Позволяет запускать обновления по расписанию.
    """
    
    def __init__(self, config: Optional[ParserConfig] = None,
                 updater: Optional[RatesUpdater] = None):
        """
        Args:
            config: Конфигурация парсера
            updater: Объект RatesUpdater (если None, создается автоматически)
        """
        self.config = config or ParserConfig()
        self.storage = RatesStorage(self.config)
        self.updater = updater or RatesUpdater(self.config, self.storage)
        
        self.scheduler_thread = None
        self.is_running = False
        self.stop_event = threading.Event()
        
        # Статистика
        self.scheduled_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.last_run_time = None
        self.next_run_time = None
        
        logger.info("ParserScheduler initialized")
    
    def start(self, interval: Optional[int] = None, run_immediately: bool = True):
        """
        Запускает планировщик.
        
        Args:
            interval: Интервал обновления в секундах (если None, используется из конфига)
            run_immediately: Если True, выполняет обновление сразу при запуске
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        if interval is None:
            interval = self.config.UPDATE_INTERVAL
        
        self.is_running = True
        self.stop_event.clear()
        
        logger.info(f"Starting scheduler with {interval}s interval")
        
        # Запускаем сразу если нужно
        if run_immediately:
            self._run_update_async()
        
        # Настраиваем расписание
        schedule.every(interval).seconds.do(self._run_update_async)
        
        # Запускаем поток планировщика
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="ParserSchedulerThread"
        )
        self.scheduler_thread.start()
        
        # Рассчитываем время следующего запуска
        self._calculate_next_run_time()
        
        logger.info("Scheduler started successfully")
    
    def stop(self):
        """Останавливает планировщик."""
        if not self.is_running:
            return
        
        logger.info("Stopping scheduler...")
        
        self.is_running = False
        self.stop_event.set()
        
        # Очищаем все запланированные задачи
        schedule.clear()
        
        # Ждем завершения потока
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Scheduler stopped")
    
    def _scheduler_loop(self):
        """
        Основной цикл планировщика.
        """
        logger.info("Scheduler loop started")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Запускаем запланированные задачи
                schedule.run_pending()
                
                # Ждем некоторое время перед следующей проверкой
                time.sleep(1)
                
                # Обновляем время следующего запуска
                self._calculate_next_run_time()
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Ждем перед повторной попыткой
        
        logger.info("Scheduler loop stopped")
    
    def _run_update_async(self):
        """
        Выполняет обновление курсов в отдельном потоке.
        """
        # Увеличиваем счетчик запланированных запусков
        self.scheduled_runs += 1
        self.last_run_time = datetime.now()
        
        # Запускаем в отдельном потоке чтобы не блокировать планировщик
        thread = threading.Thread(
            target=self._run_update_sync,
            daemon=True,
            name=f"UpdateThread_{self.scheduled_runs}"
        )
        thread.start()
    
    def _run_update_sync(self):
        """
        Синхронное выполнение обновления курсов.
        """
        logger.info(f"Starting scheduled update #{self.scheduled_runs}")
        
        try:
            result = self.updater.run_update()
            
            if result.get('status') == 'success':
                self.successful_runs += 1
                logger.info(f"Scheduled update #{self.scheduled_runs} completed successfully")
            else:
                self.failed_runs += 1
                logger.error(f"Scheduled update #{self.scheduled_runs} failed")
                
        except Exception as e:
            self.failed_runs += 1
            logger.error(f"Scheduled update #{self.scheduled_runs} failed with error: {e}")
    
    def _calculate_next_run_time(self):
        """Рассчитывает время следующего запланированного запуска."""
        try:
            jobs = schedule.get_jobs()
            if jobs:
                # Берем время следующего запуска первого задания
                self.next_run_time = jobs[0].next_run
            else:
                self.next_run_time = None
        except Exception:
            self.next_run_time = None
    
    def get_status(self) -> dict:
        """
        Возвращает текущий статус планировщика.
        
        Returns:
            Словарь со статусом
        """
        jobs = schedule.get_jobs()
        
        return {
            'is_running': self.is_running,
            'scheduled_runs': self.scheduled_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'next_run_time': self.next_run_time.isoformat() if self.next_run_time else None,
            'scheduled_jobs': len(jobs),
            'update_interval': self.config.UPDATE_INTERVAL,
            'rates_ttl': self.config.RATES_TTL,
        }
    
    def add_custom_schedule(self, cron_expression: str, job_func: Callable):
        """
        Добавляет пользовательское расписание в формате cron.
        
        Args:
            cron_expression: Выражение cron (например, "*/15 * * * *")
            job_func: Функция для выполнения
            
        Returns:
            Созданное задание
        """
        try:
            # Парсим cron выражение
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 parts")
            
            minute, hour, day, month, day_of_week = parts
            
            # Создаем задание
            job = schedule.every()
            
            # Настраиваем интервал
            if minute != '*':
                if minute.startswith('*/'):
                    interval = int(minute[2:])
                    job = job.minute.every(interval)
                else:
                    job = job.minute.at(minute)
            
            if hour != '*':
                if hour.startswith('*/'):
                    interval = int(hour[2:])
                    job = job.hour.every(interval)
                else:
                    job = job.hour.at(hour)
            
            if day != '*':
                job = job.day
            
            if day_of_week != '*':
                # Поддержка дней недели
                day_map = {
                    '0': 'sunday', '1': 'monday', '2': 'tuesday',
                    '3': 'wednesday', '4': 'thursday', '5': 'friday',
                    '6': 'saturday',
                    'sun': 'sunday', 'mon': 'monday', 'tue': 'tuesday',
                    'wed': 'wednesday', 'thu': 'thursday', 'fri': 'friday',
                    'sat': 'saturday'
                }
                
                day_name = day_map.get(day_of_week.lower(), day_of_week.lower())
                job = getattr(job, day_name)
            
            # Добавляем функцию
            job.do(job_func)
            
            logger.info(f"Added custom schedule: {cron_expression}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to add custom schedule: {e}")
            raise
    
    def run_once(self):
        """
        Выполняет однократное обновление вне расписания.
        """
        logger.info("Running one-time update...")
        self._run_update_sync()
    
    def run_for_duration(self, duration_seconds: int):
        """
        Запускает планировщик на указанное время.
        
        Args:
            duration_seconds: Время работы в секундах
        """
        logger.info(f"Running scheduler for {duration_seconds} seconds...")
        
        self.start(run_immediately=True)
        
        try:
            time.sleep(duration_seconds)
        finally:
            self.stop()
        
        logger.info(f"Scheduler ran for {duration_seconds} seconds")
    
    def __enter__(self):
        """Поддержка контекстного менеджера."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Поддержка контекстного менеджера."""
        self.stop()


class ManualScheduler:
    """
    Упрощенный планировщик для ручного управления обновлениями.
    Не требует внешних зависимостей.
    """
    
    def __init__(self, updater: RatesUpdater):
        """
        Args:
            updater: Объект RatesUpdater
        """
        self.updater = updater
        self.update_thread = None
        self.stop_flag = False
    
    def start_periodic_updates(self, interval: int = 300):
        """
        Запускает периодические обновления в отдельном потоке.
        
        Args:
            interval: Интервал обновления в секундах
        """
        if self.update_thread and self.update_thread.is_alive():
            logger.warning("Periodic updates already running")
            return
        
        self.stop_flag = False
        
        def update_loop():
            logger.info(f"Starting periodic updates every {interval}s")
            
            while not self.stop_flag:
                try:
                    self.updater.run_update()
                except Exception as e:
                    logger.error(f"Periodic update failed: {e}")
                
                # Ждем указанный интервал
                for _ in range(interval):
                    if self.stop_flag:
                        break
                    time.sleep(1)
            
            logger.info("Periodic updates stopped")
        
        self.update_thread = threading.Thread(
            target=update_loop,
            daemon=True,
            name="ManualSchedulerThread"
        )
        self.update_thread.start()
    
    def stop_periodic_updates(self):
        """Останавливает периодические обновления."""
        self.stop_flag = True
        
        if self.update_thread:
            self.update_thread.join(timeout=5)
            self.update_thread = None
        
        logger.info("Periodic updates stopped")
