# ValutaTrade Hub

Платформа для отслеживания и симуляции торговли валютами с поддержкой фиатных денег и криптовалюты.
**Поддерживаемые валюты**
Фиатные: USD, EUR, GBP, RUB, JPY, CHF, CAD, AUD, CNY
Криптовалюты: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, DOT

## Функциональность

- Регистрация и аутентификация пользователей
- Управление портфелем с множеством валют
- Покупка/продажа валют с автоматическим расчетом стоимости
- Получение актуальных курсов валют
- Парсинг курсов из внешних API (CoinGecko, ExchangeRate-API)
- Логирование всех операций
- Валидация данных и обработка ошибок

## Структура проекта

    finalproject_barsukov_M25-555/
    ├── data/                   # Файлы данных (JSON)
    │ ├── users.json            # Пользователи
    │ ├── portfolios.json       # Портфели пользователей
    │ ├── rates.json            # Текущие курсы валют
    │ └── exchange_rates.json   # История курсов
    ├── logs/                   # Логи приложения
    ├── valutatrade_hub/        # Основной код
    │ ├── core/                 # Бизнес-логика
    │ │ ├── models.py           # Классы User, Wallet, Portfolio
    │ │ ├── usecases.py         # Основные сценарии
    │ │ ├── currencies.py       # Иерархия валют
    │ │ ├── exceptions.py       # Пользовательские исключения
    │ │ └── utils.py            # Вспомогательные функции
    │ ├── infra/                # Инфраструктура
    │ │ ├── settings.py         # Singleton для конфигурации
    │ │ └── database.py         # Singleton для работы с данными
    │ ├── parser_service/       # Сервис парсинга курсов
    │ │ ├── api_clients.py      # Клиенты для API
    │ │ ├── updater.py          # Обновление курсов
    │ │ ├── storage.py          # Работа с хранилищем
    │ │ └── config.py           # Конфигурация парсера
    │ ├── cli/                  # Командный интерфейс
    │ │ └── interface.py        # Реализация команд CLI
    │ ├── logging_config.py     # Настройка логирования
    │ └── decorators.py         # Декораторы (логирование)
    ├── main.py                 # Точка входа
    ├── Makefile                # Автоматизация
    ├── pyproject.toml          # Конфигурация Poetry
    ├── test_app.py             # Тестовый скрипт
    └── README.md               # Документация

## Установка

    git clone https://github.com/MikhailBrock/finalproject_barsukov_M25-555.git
    cd finalproject_barsukov_M25-555

## Команды Makefile

    make install      # Установка зависимостей
    export EXCHANGERATE_API_KEY="ваш_ключ_здесь" # Установка переменной окружения
    make project      # Запуск приложения
    make build        # Сборка пакета
    make lint         # Проверка кода
    make format       # Форматирование кода
    make test         # Запуск тестов


## Команды приложения

    # Регистрация нового пользователя
    poetry run python3 main.py register --username mikhail --password 1234

    # Вход в систему
    poetry run python3 main.py login --username mikhail --password 1234

    # Просмотр портфеля
    poetry run python3 main.py show-portfolio --base USD

    # Покупка валюты
    poetry run python3 main.py buy --currency BTC --amount 0.05

    # Продажа валюты
    poetry run python3 main.py sell --currency BTC --amount 0.01

    # Получение текущего курса
    poetry run python3 main.py get-rate --from USD --to BTC

    # Обновление курсов валют
    poetry run python3 main.py update-rates

    # Просмотр всех курсов
    poetry run python3 main.py show-rates --top 5

## Конфиг

    [tool.valutatrade]
    data_dir = "data"                # Папка с данными
    rates_ttl_seconds = 300          # TTL кэша курсов (5 минут)
    default_base_currency = "USD"    # Базовая валюта по умолчанию
    log_level = "INFO"               # Уровень логирования
    log_file = "logs/actions.log"    # Файл логов
    
## Обработка ошибок

Приложение обрабатывает следующие ошибки:

    *InsufficientFundsError* - недостаточно средств для операции
    *CurrencyNotFoundError* - неизвестная валюта
    *ApiRequestError* - ошибка при обращении к внешнему API
    *UserNotFoundError* - пользователь не найден
    *AuthenticationError* - ошибка аутентификации

Все ошибки логируются в logs/actions.log и отображаются пользователю в понятном формате.

## Демонстрация

https://asciinema.org/a/r5kB4bwtAsefnilwxJa1g6LVf

*или файл "demo3.cast"

## Автор

Михаил Барсуков - M25-555
