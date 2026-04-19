# VPN Subscription Service

HAPP-совместимый сервис для создания зашифрованных ссылок на подписку с ограниченным сроком действия и ограничением по количеству девайсов.

## Статус проекта

**MVP Foundation** — базовая инфраструктура с FastAPI + PostgreSQL.

## Технологии

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x (async)
- PostgreSQL 16
- Docker Compose

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repository-url>
cd vpn_service
cp .env.example .env
# Отредактируйте .env и установите безопасный ADMIN_PASSWORD
```

### 2. Запуск

```bash
docker compose up -d --build
```

### 3. Проверка

**Health check (публичный):**
```bash
curl http://localhost:8000/api/v1/health
```

Ожидаемый ответ:
```json
{"status": "ok", "database": "connected"}
```

**Admin test (защищённый):**
```bash
curl -u admin:change_me_in_production http://localhost:8000/api/v1/admin/test
```

Ожидаемый ответ:
```json
{"message": "Admin access confirmed", "timestamp": "2026-04-19T06:42:00Z"}
```

### 4. Остановка

```bash
docker-compose down
```

## API Endpoints

### Public

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/v1/health` | Health check с проверкой БД |

### Protected (требует HTTP Basic Auth)

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/v1/admin/test` | Проверка административного доступа |
| GET | `/api/v1/admin/vpn-sources` | Список VPN источников (без URI) |
| GET | `/api/v1/admin/vpn-sources/{id}` | Детальная информация о VPN источнике (с URI) |
| POST | `/api/v1/admin/vpn-sources` | Создание VPN источника |
| POST | `/api/v1/admin/vpn-sources/batch` | Batch создание VPN источников |
| PATCH | `/api/v1/admin/vpn-sources/{id}` | Обновление VPN источника |
| DELETE | `/api/v1/admin/vpn-sources/{id}` | Удаление VPN источника |
| GET | `/api/v1/admin/vpn-source-tags` | Список тегов |
| POST | `/api/v1/admin/vpn-source-tags` | Создание тега |

### Query Parameters

**GET `/api/v1/admin/vpn-sources`:**
- `tags` (optional): фильтрация по тегам, comma-separated slugs (например, `tags=eu,premium`)
- `is_active` (optional): фильтрация по статусу (`true`/`false`)

### Supported VPN Protocols

Поддерживаемые схемы URI:
- `vless://` — VLESS protocol
- `trojan://` — Trojan protocol
- `vmess://` — VMess protocol (base64 encoded JSON)
- `ss://` — Shadowsocks
- `ssr://` — ShadowsocksR

## Архитектура

Проект следует DDD и модульному монолиту:

```
src/
├── domain/           # Сущности, value objects, порты репозиториев
├── application/      # Use cases, оркестрация
├── infrastructure/   # БД, адаптеры, внешние сервисы
│   └── db/
│       ├── database.py
│       └── models/
└── presentation/     # HTTP слой
    └── http/
        ├── dependencies.py
        ├── health_router.py
        └── admin_router.py
```

## Авторизация

⚠️ **ВНИМАНИЕ:** Текущая реализация использует HTTP Basic Auth как **временное bootstrap-решение**.

Это решение:
- Подходит только для внутреннего административного контура
- Требует HTTPS в продакшене (Base64 не шифрование)
- Будет заменено на сервисную авторизацию (client credentials flow)

## Разработка

### Установка зависимостей локально

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Запуск тестов

```bash
pytest
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DB_USER` | `vpn_user` | Пользователь PostgreSQL |
| `DB_PASSWORD` | `change_me_in_production` | Пароль PostgreSQL |
| `DB_NAME` | `vpn_db` | Имя базы данных |
| `ADMIN_USERNAME` | `admin` | Логин администратора (bootstrap) |
| `ADMIN_PASSWORD` | `change_me_in_production` | Пароль администратора (bootstrap) |
| `ENVIRONMENT` | `dev` | Окружение: dev, staging, prod |

## Roadmap

1. ✅ MVP Foundation
2. ✅ CRUD для VPN источников и тегов (текущий этап)
3. 🔜 Сервисная авторизация (client credentials)
4. 🔜 Выпуск временных подписок
5. 🔜 Контроль срока действия и лимита устройств
6. 🔜 Аудит и наблюдаемость
7. 🔜 OAuth2/OIDC и личный кабинет