# План: CRUD хендлеры для VPN источников

## Контекст

Создание HTTP API для управления исходными VPN-ссылками (хранение, получение, добавление, изменение).

**Поддомен:** `vpn_catalog`

**Текущее состояние:**
- MVP Foundation готов: FastAPI + PostgreSQL, HTTP Basic Auth (bootstrap)
- Пустые слои domain/application/infrastructure
- Нет миграций

## Варианты реализации

### 1. Валидация VPN URI

**Вариант A: Строгая валидация форматов (выбран)**
- Парсинг и проверка известных схем: `vless://`, `trojan://`, `vmess://`, `ss://`, `ssr://`
- Проверка структуры URI, извлечение параметров
- При batch upload — возврат списка невалидных ссылок с объяснением ошибок
- Плюсы: данные гарантированно корректны, защита от мусора, понятные ошибки для пользователя
- Минусы: сложность, нужно поддерживать новые форматы

**Вариант B: Минимальная валидация**
- Проверка только на непустоту и базовый формат URL
- Хранение "как есть", валидация при использовании в подписке
- Плюсы: простота, гибкость, поддержка любых будущих форматов
- Минусы: возможен мусор в БД, нет понятных ошибок при загрузке

**Выбор:** Вариант A. Пользователь явно требует валидацию с понятными ошибками. Batch upload должен возвращать какие ссылки не загрузились и почему.

**Реализация валидации:**
- Domain: `VpnUriValidator` — доменный сервис для проверки схемы и структуры
- Infrastructure: конкретные парсеры для каждого протокола (vless, trojan, vmess, ss, ssr)
- При batch upload: collect all errors, return structured response with success/failure per item

### 2. Теги и группировка

**Вариант A: Включить теги сразу (выбран)**
- Таблица `vpn_source_tags` (id, name, slug, created_at)
- Таблица `vpn_source_tag_associations` (vpn_source_id, tag_id)
- Many-to-many связь между vpn_sources и tags
- Гибкая фильтрация по тегам при запросе
- Плюсы: future-proof, сразу готова структура для группировки
- Минусы: чуть больше кода и миграций

**Вариант B: Только базовые поля**
- `name`, `uri`, `description`, `is_active`, `created_at`, `updated_at`
- Теги добавить позже отдельной миграцией
- Плюсы: простота, фокус на MVP
- Минусы: потребуется миграция для тегов

**Выбор:** Вариант A. Теги — важная часть домена `vpn_catalog`. Удобная группировка и фильтрация нужна уже на этапе MVP для управления большим количеством источников.

**Реализация тегов:**
- Domain: `VpnSourceTag` entity, `TagId` value object
- Infrastructure: `vpn_source_tags` + `vpn_source_tag_associations` таблицы
- API: возможность задавать теги при создании/обновлении источника
- Query: фильтрация по тегам в GET endpoint (опциональный параметр `tags=slug1,slug2`)

### 3. Обновление: PATCH vs PUT

**Вариант A: PATCH с частичным обновлением (выбран)**
- Обновляются только переданные поля
- Плюсы: удобнее для клиентов, меньше данных в запросе
- Минусы: чуть сложнее логика

**Вариант B: PUT с полной заменой**
- Все поля обязательны
- Плюсы: простота
- Минусы: неудобно для частичных изменений

**Выбор:** Вариант A. PATCH — стандарт для частичных обновлений в REST API.

## Структура файлов

### Domain Layer

```
src/domain/vpn_catalog/
├── __init__.py
├── entities.py           # VpnSource, VpnSourceTag entities
├── value_objects.py      # VpnSourceId, VpnUri, TagId, TagSlug
├── repositories.py       # VpnSourceRepository, VpnSourceTagRepository ports
├── validators.py         # VpnUriValidator domain service interface
└── validation_errors.py  # ValidationError value objects
```
src/domain/vpn_catalog/
├── __init__.py
├── entities.py           # VpnSource entity
├── value_objects.py      # VpnSourceId, VpnUri
├── repositories.py       # VpnSourceRepository port
└── validators.py         # VpnUriValidator domain service
├── validation_errors.py  # ValidationError value objects
```

### Application Layer

```
src/application/vpn_catalog/
├── __init__.py
├── use_cases.py       # GetAll, GetById, Create, CreateBatch, Update, Delete use cases
├── tag_use_cases.py   # GetAllTags, CreateTag use cases
└── dto.py             # Input/Output DTOs, BatchResult DTO, TagDTO
```

### Infrastructure Layer

```
src/infrastructure/db/
├── models/
│   ├── __init__.py
│   ├── vpn_source.py       # SQLAlchemy model for vpn_sources
│   └── vpn_source_tag.py   # SQLAlchemy models for vpn_source_tags + association table
├── repositories/
│   ├── __init__.py
│   ├── vpn_source.py       # Repository implementation
│   └── vpn_source_tag.py   # Tag repository implementation
└── validators/
    ├── __init__.py
    └── vpn_uri.py          # Concrete validators for each protocol
```

### Presentation Layer

```
src/presentation/http/
├── vpn_sources_router.py      # HTTP endpoints for VPN sources
├── vpn_source_tags_router.py  # HTTP endpoints for tags
└── dto/
    └── vpn_sources.py         # Request/Response schemas (sources + tags)
```

## API Endpoints

**ВАЖНО:** Все endpoints доступны **только администратору** через HTTP Basic Auth (bootstrap).  
В будущем будет заменено на сервисную авторизацию с client credentials flow.

### GET `/api/v1/admin/vpn-sources`
- Авторизация: Admin (HTTP Basic) — **обязательно**
- Query params: 
  - `tags` (optional): фильтрация по тегам, comma-separated slugs (`tags=eu,premium`)
  - `is_active` (optional): фильтрация по статусу (`true`/`false`)
- Response: список VPN источников с тегами
  ```json
  {
    "items": [
      {
        "id": "...",
        "name": "Server EU-1",
        "description": "...",
        "is_active": true,
        "tags": [{"id": "...", "name": "Europe", "slug": "eu"}, {"id": "...", "name": "Premium", "slug": "premium"}],
        "created_at": "...",
        "updated_at": "..."
      }
    ]
  }
  ```
- **НЕ** возвращать полный `uri` в списке (security concern)

### GET `/api/v1/admin/vpn-sources/{id}`
- Авторизация: Admin — **обязательно**
- Response: детальная информация о источнике (включая uri для редактирования)

### GET `/api/v1/admin/vpn-source-tags`
- Авторизация: Admin — **обязательно**
- Response: список всех доступных тегов
  ```json
  {
    "items": [
      {"id": "...", "name": "Europe", "slug": "eu", "created_at": "..."},
      {"id": "...", "name": "Premium", "slug": "premium", "created_at": "..."}
    ]
  }
  ```

### POST `/api/v1/admin/vpn-source-tags`
- Авторизация: Admin — **обязательно**
- Body: name, slug (опционально, генерируется из name если не передан)
- Response: созданный тег (201)

### POST `/api/v1/admin/vpn-sources`
- Авторизация: Admin — **обязательно**
- Body: 
  ```json
  {
    "name": "...",
    "uri": "...",
    "description": "...",  // optional
    "is_active": true,      // optional, default: true
    "tags": ["eu", "premium"]  // optional, array of slugs
  }
  ```
- Валидация uri через VpnUriValidator
- Теги: поиск по slug, создание новых если не найдены (опционально — можно требовать существующие)
- Response: созданный источник (201) или ошибки валидации (400)

### POST `/api/v1/admin/vpn-sources/batch`
- Авторизация: Admin — **обязательно**
- Body: массив объектов [{name, uri, description?, is_active?, tags?}, ...]
- Batch upload с валидацией каждой ссылки
- Теги: назначаются для каждого источника
- Response: структура с результатами
  ```json
  {
    "created": [
      {"id": "...", "name": "...", "tags": [...]}
    ],
    "failed": [
      {
        "index": 0,
        "name": "...",
        "uri": "...",
        "error": "Invalid URI scheme: unknown:// is not supported..."
      }
    ],
    "total": 5,
    "success_count": 3,
    "failed_count": 2
  }
  ```

### PATCH `/api/v1/admin/vpn-sources/{id}`
- Авторизация: Admin — **обязательно**
- Body: name, uri, description, is_active, tags (все опционально)
- Если uri передан — валидация через VpnUriValidator
- Если tags передан — полная замена тегов (не additive)
- Response: обновлённый источник (200) или ошибки валидации (400)

### DELETE `/api/v1/admin/vpn-sources/{id}`
- Авторизация: Admin — **обязательно**
- Response: 204 No Content (soft delete — set is_active=false) или hard delete

## Схема данных

### Таблица `vpn_sources`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| name | VARCHAR(255) | NO | Человекочитаемое имя |
| uri | TEXT | NO | VPN URI (vless://, trojan://, и т.д.) |
| description | TEXT | YES | Описание |
| is_active | BOOLEAN | NO | Активен ли источник |
| created_at | TIMESTAMPTZ | NO | Время создания |
| updated_at | TIMESTAMPTZ | NO | Время обновления |

### Таблица `vpn_source_tags`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| name | VARCHAR(100) | NO | Человекочитаемое имя тега |
| slug | VARCHAR(100) | NO | URL-friendly slug (unique) |
| created_at | TIMESTAMPTZ | NO | Время создания |

### Таблица `vpn_source_tag_associations`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| vpn_source_id | UUID | NO | FK → vpn_sources.id |
| tag_id | UUID | NO | FK → vpn_source_tags.id |

**Unique constraint:** `(vpn_source_id, tag_id)` — один тег не может быть назначен дважды одному источнику

### Индексы
- `idx_vpn_sources_is_active` на `is_active` (для фильтрации активных)
- `idx_vpn_source_tags_slug` на `slug` (unique, для поиска по slug)
- `idx_vpn_source_tag_assoc_source` на `vpn_source_id` (для загрузки тегов источника)
- `idx_vpn_source_tag_assoc_tag` на `tag_id` (для поиска источников по тегу)

## Поддерживаемые VPN протоколы и валидация

### Схемы URI

Поддерживаемые схемы:
- `vless://` — VLESS protocol
- `trojan://` — Trojan protocol  
- `vmess://` — VMess protocol (base64 encoded)
- `ss://` — Shadowsocks
- `ssr://` — ShadowsocksR

### Валидация URI

**Domain Layer:**
- `VpnUriValidator` — интерфейс доменного сервиса валидации
- Возвращает `ValidationResult` (success или list of errors)

**Infrastructure Layer:**
- Concrete validators для каждого протокола
- Парсинг URI, проверка обязательных параметров
- Обнаружение отсутствующих или некорректных параметров

**Типичные ошибки валидации:**
- `Unsupported scheme: "unknown://"` — неподдерживаемый протокол
- `Missing required parameter: "host"` — отсутствует host
- `Missing required parameter: "port"` — отсутствует port
- `Invalid port: "abc"` — port не число
- `Missing UUID: vless requires UUID in path"` — для VLESS
- `Invalid UUID format` — некорректный UUID

**Batch upload behavior:**
- Все ссылки валидируются до сохранения
- Валидные — сохраняются, невалидные — возвращаются в `failed` list
- Ошибки агрегируются с индексом ссылки в массиве

## Файлы для создания (22 файла)

### Domain

1. `src/domain/vpn_catalog/__init__.py` — экспорт домена
2. `src/domain/vpn_catalog/entities.py` — VpnSource, VpnSourceTag entities
3. `src/domain/vpn_catalog/value_objects.py` — VpnSourceId, VpnUri, TagId, TagSlug
4. `src/domain/vpn_catalog/repositories.py` — VpnSourceRepository, VpnSourceTagRepository ports
5. `src/domain/vpn_catalog/validators.py` — VpnUriValidator domain service interface
6. `src/domain/vpn_catalog/validation_errors.py` — ValidationError value objects

### Application

7. `src/application/vpn_catalog/__init__.py` — экспорт application
8. `src/application/vpn_catalog/dto.py` — DTO классы, BatchResult DTO, TagDTO
9. `src/application/vpn_catalog/use_cases.py` — GetAll, GetById, Create, CreateBatch, Update, Delete use cases
10. `src/application/vpn_catalog/tag_use_cases.py` — GetAllTags, CreateTag use cases

### Infrastructure

11. `src/infrastructure/db/models/vpn_source.py` — SQLAlchemy model
12. `src/infrastructure/db/models/vpn_source_tag.py` — SQLAlchemy models (tag + association)
13. `src/infrastructure/db/repositories/__init__.py`
14. `src/infrastructure/db/repositories/vpn_source.py` — Repository impl
15. `src/infrastructure/db/repositories/vpn_source_tag.py` — Tag repository impl
16. `src/infrastructure/db/validators/__init__.py`
17. `src/infrastructure/db/validators/vpn_uri.py` — Concrete validators

### Presentation

18. `src/presentation/http/vpn_sources_router.py` — Router for vpn sources
19. `src/presentation/http/vpn_source_tags_router.py` — Router for tags
20. `src/presentation/http/dto/__init__.py`
21. `src/presentation/http/dto/vpn_sources.py` — Request/Response schemas

### Migrations

22. Инициализация Alembic и миграция (vpn_sources + vpn_source_tags + associations)

## Архитектурные решения

### 1. DDD Layers

**Router (Presentation) → Use Case (Application) → Repository (Infrastructure via Domain Port)**

- Router: принимает HTTP запрос, вызывает use case, возвращает HTTP ответ
- Use Case: бизнес-логика, не зависит от FastAPI
- Repository: персистентность, реализует доменный порт

### 2. DTO vs Pydantic Schema

- **Request/Response schemas** (в presentation): для API контракта
- **DTO** (в application): для передачи данных между слоями
- **Entity** (в domain): для бизнес-логики

### 3. Обработка ошибок

Use case возвращает Result или выбрасывает доменные исключения.
Router мапит ошибки в HTTP статусы.

### 4. Безопасность логирования

- **НИКОГДА** не логировать `uri` целиком
- Логировать только `id`, `name`, `is_active`
- При ошибках — mask/redact чувствительные данные

## Замечания по безопасности

1. `uri` содержит чувствительные данные (ключи, пароли)
2. В логах — только идентификаторы, не URI
3. Эндпоинты защищены Admin Auth (bootstrap)
4. В будущем — audit logging создания/изменения источников

## Definition of Done

- [ ] Domain: VpnSource + VpnSourceTag entities, value objects, repository ports, VpnUriValidator interface
- [ ] Application: DTOs, use cases (vpn sources + tags)
- [ ] Infrastructure: ORM models (vpn_sources, vpn_source_tags, associations), repositories, validators
- [ ] Presentation: routers (vpn sources + tags), schemas
- [ ] Migration: Alembic init, create tables (vpn_sources, vpn_source_tags, vpn_source_tag_associations)
- [ ] Tests: unit для validators, unit для use cases, integration для endpoints
- [ ] Security: нет логирования URI в списках, только в детальном GET
- [ ] Security: все endpoints требуют Admin auth
- [ ] Tags: CRUD для тегов, назначение тегов источникам, фильтрация по тегам
- [ ] Documentation: обновить README с новыми endpoints
- [ ] Batch upload: возвращает структурированные ошибки для каждой невалидной ссылки

## Порядок реализации

1. Domain layer: VpnSource + VpnSourceTag entities, value objects, repository ports, VpnUriValidator interface
2. Infrastructure: ORM models (vpn_sources, vpn_source_tags, associations)
3. Infrastructure: concrete validators (vless, trojan, vmess, ss, ssr)
4. Migration: Alembic init + create all tables
5. Application: DTOs, use cases (vpn sources + tags)
6. Infrastructure: repository implementations (vpn sources + tags)
7. Presentation: routers, schemas
8. Wire everything in main.py
9. Tests: validators, use cases, endpoints
10. Security review: check no URI logging in lists