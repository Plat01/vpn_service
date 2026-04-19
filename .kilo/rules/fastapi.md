# FastAPI Rules

## Основной стек

Если нет сильного обоснования иного решения, используй:

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pytest
- httpx / pytest-asyncio для API-тестов
- `uv` или `poetry` только если это согласуется с проектом, но по умолчанию не навязывай лишний инструмент

## API conventions

- Версионируй API: `/api/v1/...`
- Разделяй `admin`, `internal`, `public` маршруты, если это помогает модели прав
- Делай явные request/response schemas
- Не возвращай ORM объекты напрямую
- Не смешивай внутренние и внешние DTO

## Handlers

Route handler обязан:
- принять HTTP-запрос;
- провалидировать вход через schema;
- вызвать use case;
- преобразовать результат в response DTO.

Route handler не должен:
- содержать бизнес-логику выбора VPN-ссылок;
- считать TTL/device limit;
- делать сложную работу с БД;
- напрямую шифровать HAPP-ссылку.

## Dependencies

FastAPI dependencies должны использоваться для:
- получения текущего клиента/пользователя;
- предоставления use case и repository implementations;
- выдачи clock/crypto/auth providers;
- cross-cutting concerns.

Не использовать dependencies как место, где прячется доменная логика.

## Pydantic

- Request/response models живут отдельно от domain entities.
- Не использовать Pydantic schema как замену domain модели.
- Для чувствительных полей продумывать исключение из repr/json.
- Для enum и ограничений использовать явные типы.

## SQLAlchemy

- ORM-модели держать в infrastructure/db/models.
- Не тянуть ORM-сущности внутрь domain.
- Использовать явные репозитории.
- Все изменения схемы — через Alembic migrations.
- Не делать "ручные изменения в БД, потом как-нибудь миграцию".

## Ошибки

- Разделяй domain/application/infrastructure ошибки.
- В HTTP слой преобразуй ошибки в предсказуемые ответы.
- Не отдавай traceback и детали внутренней схемы БД наружу.

## Background processing

Если появляется фоновая обработка:
- задача должна быть идемпотентной;
- payload минимальный;
- бизнес-правила всё равно должны жить в application/domain;
- outbox/event-driven подход предлагать только когда он действительно оправдан.

## Тестирование

Минимум:
- unit для value objects, policies, TTL/device limit;
- integration для repositories и auth;
- API tests для критичных endpoint flows.

При добавлении эндпоинта минимум нужно покрыть:
- happy path;
- unauthorized/forbidden;
- invalid input;
- expired/revoked subscription, если применимо.

## Документирование

Для каждой нетривиальной API-фичи агент должен описать:
- назначение;
- request schema;
- response schema;
- auth requirements;
- бизнес-ограничения;
- ошибки.
