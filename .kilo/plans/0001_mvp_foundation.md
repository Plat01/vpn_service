# План: Docker Compose шаблон для VPN Subscription Service (MVP Foundation)

## Контекст

Создаём минимальный docker-compose шаблон для локальной разработки с FastAPI + PostgreSQL. Два тестовых эндпоинта: публичный (health check) и защищённый (bootstrap admin password).

**Поддомен:** identity (bootstrap авторизация)

## Варианты реализации

### Вариант A: HTTP Basic Auth (bootstrap)

- Admin password в .env
- HTTP Basic для защищённого эндпоинта
- Помечен как временное решение
- Легко заменить на client credentials flow

### Вариант B: API Key в заголовке

- X-API-Key header
- Проще для скриптов и自动化
- Не стандартный механизм для браузеров

### Вариант C: Сервисная авторизация сразу

- Таблица service_clients
- Token endpoint
- JWT access tokens

**Выбран вариант A**, потому что:
- Это bootstrap-решение для быстрого старта
- Стандартный механизм, поддерживаемый всеми HTTP-клиентами
- Легко тестировать через curl и Postman
- Явно помечен как временное, не блокирует эволюцию
- Переход на вариант C предусмотрен архитектурой

**Почему не C:** Для MVP Foundation избыточно. Сервисная авторизация будет в `0002_service_auth.md`.

## Структура проекта

```text
vpn_service/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .dockerignore
├── pyproject.toml
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── presentation/
│   │   └── http/
│   │       ├── health_router.py
│   │       ├── admin_router.py
│   │       └── dependencies.py
│   ├── application/
│   ├── domain/
│   └── infrastructure/
│       └── db/
│           ├── database.py
│           └── models/
├── tests/
│   ├── conftest.py
│   └── test_health.py
└── README.md
```

## Файлы для создания (15 файлов)

### Infrastructure

1. **`docker-compose.yml`** — сервисы app + db, volumes, networks
2. **`Dockerfile`** — multi-stage build, Python 3.12-slim
3. **`requirements.txt`** — зависимости проекта
4. **`.env.example`** — шаблон переменных окружения
5. **`.dockerignore`** — исключения для build context

### Application Layer

6. **`src/main.py`** — FastAPI app factory, роутеры, lifespan
7. **`src/config.py`** — pydantic-settings для конфигурации

### Infrastructure Layer

8. **`src/infrastructure/db/database.py`** — async engine, session factory

### Presentation Layer

9. **`src/presentation/http/health_router.py`** — GET /api/v1/health (public)
10. **`src/presentation/http/admin_router.py`** — GET /api/v1/admin/test (protected)
11. **`src/presentation/http/dependencies.py`** — get_current_admin dependency

### Domain Layer (placeholder)

12. **`src/domain/__init__.py`** — пустой, для будущих сущностей

### Tests

13. **`tests/conftest.py`** — pytest fixtures
14. **`tests/test_health.py`** — тесты health endpoint

### Documentation

15. **`README.md`** — инструкция по развёртыванию

## API Endpoints

### Public: `/api/v1/health`

```json
GET /api/v1/health
Response 200: {"status": "ok", "database": "connected"}
```

### Protected: `/api/v1/admin/test`

```json
GET /api/v1/admin/test
Authorization: Basic admin:password
Response 200: {"message": "Admin access confirmed", "timestamp": "2026-04-19T06:42:00Z"}
Response 401: {"detail": "Invalid credentials"}
```

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://vpn_user:vpn_pass@db:5432/vpn_db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_in_production
ENVIRONMENT=dev
```

## Архитектурные решения

### 1. Async SQLAlchemy

**Выбор:** Async SQLAlchemy 2.x с asyncpg

**Почему:**
- FastAPI natively async
- Лучшая производительность для I/O-bound
- Современный стандарт

### 2. Разделение роутеров

**Выбор:** health_router + admin_router отдельно

**Почему:**
- SRP (Single Responsibility Principle)
- Соответствует DDD — разные поддомены
- Легко расширять

### 3. Pydantic Settings

**Выбор:** pydantic-settings для конфигурации

**Почему:**
- Валидация при запуске
- Типизация
- Интеграция с .env

## Замечания по безопасности

1. **ADMIN_PASSWORD** в .env — в продакшене должен быть захеширован
2. **HTTP Basic Auth** — нужен HTTPS в продакшене (base64 не шифрование)
3. **Bootstrap-решение** — явно документировано как временное
4. **Transition path** — архитектура позволяет заменить на client credentials без ломки домена

## Definition of Done

- [x] Dockerfile создан
- [x] docker-compose.yml создан
- [x] .env.example создан
- [x] Структура соответствует DDD слоям
- [x] Публичный эндпоинт работает
- [x] Защищённый эндпоинт требует авторизацию
- [x] README с инструкцией
- [x] Bootstrap помечен как временное
- [x] Архитектура готова к эволюции

## Инструкция по развёртыванию (для README)

1. Клонировать проект
2. Создать `.env` из `.env.example`
3. `docker-compose up -d --build`
4. Проверить health: `curl http://localhost:8000/api/v1/health`
5. Проверить admin: `curl -u admin:change_me_in_production http://localhost:8000/api/v1/admin/test`
6. Остановка: `docker-compose down`
