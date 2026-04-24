# План: Добавление логирования с настройкой через .env

## Цель
Добавить централизованное логирование в проект с возможностью изменения уровня логирования через переменную `LOG_LEVEL` в .env файле.

## Текущее состояние
- В проекте уже используется `logging.getLogger(__name__)` в `src/application/vpn_catalog/use_cases.py`
- Централизованная настройка логирования отсутствует
- Конфигурация приложения в `src/config.py` через pydantic-settings
- .env.example содержит переменные для БД, admin credentials, environment

## Что нужно сделать

### 1. Обновить src/config.py
**Добавить поле `log_level` в Settings:**
```python
log_level: str = "INFO"
```
- Значение по умолчанию: INFO (промежуточный уровень)
- Валидация: через pydantic field validator для проверки корректности уровня

### 2. Создать src/infrastructure/logging_config.py
**Новый модуль для настройки логирования:**
- Функция `setup_logging(log_level: str) -> None`
- Настройка формата: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Настройка уровня для корневого logger
- Настройка уровня для uvicorn, sqlalchemy и других библиотек
- Использование logging.basicConfig() для простоты

**Формат логов:**
```
2024-01-15 10:30:45,123 - src.application.vpn_catalog.use_cases - INFO - VpnSource created: id=abc123
```

### 3. Обновить src/main.py
**Инициализация логирования в lifespan:**
- Импортировать `setup_logging` и `settings`
- Вызвать `setup_logging(settings.log_level)` в начале lifespan
- Логировать старт и остановку приложения

### 4. Обновить .env.example
**Добавить переменную LOG_LEVEL с комментариями:**
```env
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
# DEBUG - detailed debugging information
# INFO - confirmation of expected operation
# WARNING - something unexpected happened (default for production)
# ERROR - serious problem, application can continue
# CRITICAL - fatal error, application cannot continue
LOG_LEVEL=INFO
```

### 5. Обеспечить безопасность логирования
**Соблюдение правил из security.md:**
- Никогда не логировать полные VPN URI
- Никогда не логировать client secrets, tokens
- Использовать redaction/masking для чувствительных данных
- Логировать только fingerprints, IDs, статусы

## Валидация уровня логирования

Добавить validator в Settings для проверки корректности LOG_LEVEL:
```python
from pydantic import field_validator

@field_validator('log_level')
@classmethod
def validate_log_level(cls, v: str) -> str:
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if v.upper() not in valid_levels:
        raise ValueError(f'Invalid log level: {v}. Must be one of {valid_levels}')
    return v.upper()
```

## Структура файлов после изменений

```
src/
  config.py (обновлен)
  main.py (обновлен)
  infrastructure/
    logging_config.py (новый)
.env.example (обновлен)
```

## Пример использования

```python
import logging

logger = logging.getLogger(__name__)

async def some_function():
    logger.debug("Detailed debugging info")
    logger.info("Operation completed successfully")
    logger.warning("Something unexpected")
    logger.error("Serious problem occurred")
```

## Безопасность

- Чувствительные данные (VPN URI, секреты, токены) не логируются полностью
- Используются fingerprints, IDs, статусы для трассировки
- Формат логов безопасен и не раскрывает внутренние детали

## Тестирование

После реализации:
1. Запустить приложение с `LOG_LEVEL=DEBUG` - должны видеть debug логи
2. Изменить на `LOG_LEVEL=ERROR` - debug и info логи должны исчезнуть
3. Проверить, что логи uvicorn, sqlalchemy также управляются уровнем

## Замечания

- Используется стандартный модуль `logging`, не требуется установка дополнительных пакетов
- Конфигурация простая, может быть расширена в будущем (структурированные логи, file handler, etc.)
- Уровни логирования для сторонних библиотек (uvicorn, sqlalchemy) могут быть настроены отдельно при необходимости