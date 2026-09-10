# Plan: Admin Handlers для создания зашифрованных HAPP-подписок

## Цель

Реализовать admin handlers для создания зашифрованных HAPP-ссылок на основе VPN-источников из `vpn_sources`, с TTL-ограничением на стороне сервиса и выбором источников по тегам.

## Выбранные ограничения

- **Шифрование**: HAPP crypt5 через `https://crypto.happ.su/api-v2.php`
- **TTL**: Контроль на стороне сервиса (HAPP не имеет встроенного TTL)
- **Выбор источников**: По тегам (admin указывает теги, сервис подбирает активные VPN)

---

## Архитектурное решение

### Bounded Context

`subscription_issuance` — новый поддомен для выпуска подписок.

### Слои

| Слой | Компоненты |
|------|------------|
| **Domain** | `SubscriptionIssue`, `SubscriptionIssueItem` entities; repository ports |
| **Application** | `CreateEncryptedSubscriptionUseCase` |
| **Infrastructure** | HAPP crypto adapter, subscription repository implementation, ORM models |
| **Presentation** | `subscription_issuance_router.py`, request/response DTO |

---

## Варианты реализации TTL

### Вариант A: TTL в URL подписки (выбран)
- Подписка — это текстовый список VPN URI с comment-меткой `#expires_at=...`
- При запросе подписки сервис проверяет TTL и либо:
  - возвращает пустой список если expired
  - возвращает конфиг если active

**Почему выбран**:
- HAPP-ссылка статична, не нужно генерировать новую при каждом TTL-изменении
- Простота: одна ссылка, TTL проверяется при обслуживании
- Контроль полностью на сервере

### Вариант B: TTL через отзыв подписки (не выбран)
- Админ вручную отзывает через admin endpoint
- HAPP-ссылка становится неактивной

**Почему отвергнут**:
- Не автоматический TTL
- Требует manual intervention

---

## Компоненты

### 1. Domain Layer

**Entities** (`src/domain/subscription_issuance/entities.py`):
```python
@dataclass
class SubscriptionIssue:
    id: SubscriptionIssueId
    public_id: str  # токен для URL подписки
    status: SubscriptionStatus (active, expired, revoked)
    expires_at: datetime
    max_devices: int | None  # для будущего расширения
    created_at: datetime
    created_by: str
    tags_used: list[str]  # snapshot тегов
    encrypted_link: str | None  # итоговая HAPP-ссылка

@dataclass
class SubscriptionIssueItem:
    id: SubscriptionIssueItemId
    subscription_issue_id: SubscriptionIssueId
    vpn_source_id: VpnSourceId
    position: int
    created_at: datetime
```

**Value Objects** (`src/domain/subscription_issuance/value_objects.py`):
- `SubscriptionIssueId`, `SubscriptionIssueItemId`, `SubscriptionStatus`

**Repository Ports** (`src/domain/subscription_issuance/repositories.py`):
- `SubscriptionIssueRepository`
- `SubscriptionIssueItemRepository`

### 2. Infrastructure Layer

**ORM Models** (`src/infrastructure/db/models/subscription_issue.py`):
- `SubscriptionIssueModel`
- `SubscriptionIssueItemModel`

**HAPP Crypto Adapter** (`src/infrastructure/happ/crypto_adapter.py`):
```python
class HappCryptoAdapter:
    async def encrypt_link(self, subscription_url: str) -> str:
        # POST https://crypto.happ.su/api-v2.php
        # {"url": subscription_url}
        # returns encrypted happ://crypt5/... link
```

**Subscription URL Generator** (`src/infrastructure/subscription/url_generator.py`):
- Интерфейс `SubscriptionConfigGenerator` с методом `generate(vpn_uris: list[str]) -> str`
- Реализация MVP: `TextListConfigGenerator` — текстовый список по одному URI на строку
- В будущем: `JsonConfigGenerator` — XRAY JSON с routing/DNS
- Паттерн Strategy для выбора формата

**Repositories** (`src/infrastructure/db/repositories/subscription_issue.py`):
- `SqlAlchemySubscriptionIssueRepository`
- `SqlAlchemySubscriptionIssueItemRepository`

### 3. Application Layer

**Use Case** (`src/application/subscription_issuance/use_cases.py`):
```python
class CreateEncryptedSubscriptionUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
        subscription_repo: SubscriptionIssueRepository,
        item_repo: SubscriptionIssueItemRepository,
        crypto_adapter: HappCryptoAdapter,
        url_generator: SubscriptionUrlGenerator,
        clock: TimeProvider,
    ):
        ...

    async def execute(
        tags: list[str],
        ttl_hours: int,
        created_by: str,
        max_devices: int | None = None,
    ) -> SubscriptionIssueResultDTO:
        # 1. Найти активные VPN по тегам
        # 2. Создать SubscriptionIssue с expires_at
        # 3. Создать SubscriptionIssueItems
        # 4. Генерировать URL подписки
        # 5. Зашифровать через HAPP API
        # 6. Сохранить encrypted_link
        # 7. Вернуть результат
```

**DTO** (`src/application/subscription_issuance/dto.py`):
- `CreateSubscriptionRequestDTO`
- `SubscriptionIssueResultDTO`

### 4. Presentation Layer

**Router** (`src/presentation/http/subscription_issuance_router.py`):
- `POST /api/v1/admin/subscriptions/encrypted` — создать зашифрованную подписку

**Request DTO** (`src/presentation/http/dto/subscription_issuance.py`):
```python
class CreateEncryptedSubscriptionRequest:
    tags: list[str]  # теги для выбора VPN
    ttl_hours: int  # срок действия в часах
    max_devices: int | None = None  # для будущего расширения
```

**Response DTO**:
```python
class EncryptedSubscriptionResponse:
    id: UUID
    encrypted_link: str  # happ://crypt5/...
    expires_at: datetime
    vpn_sources_count: int
    tags_used: list[str]
```

---

## Миграция базы данных

**File**: `alembic/versions/002_create_subscription_issues.py`

### Таблицы

**subscription_issues**:
- `id` UUID PRIMARY KEY
- `public_id` VARCHAR(36) UNIQUE — токен для URL
- `status` VARCHAR(20) — active/expired/revoked
- `expires_at` TIMESTAMP WITH TIME ZONE
- `max_devices` INTEGER NULL
- `created_at` TIMESTAMP WITH TIME ZONE
- `created_by` VARCHAR(255)
- `tags_used` TEXT[] — snapshot тегов
- `encrypted_link` TEXT NULL
- `revoked_at` TIMESTAMP WITH TIME ZONE NULL

**subscription_issue_items**:
- `id` UUID PRIMARY KEY
- `subscription_issue_id` UUID FK → subscription_issues.id
- `vpn_source_id` UUID FK → vpn_sources.id
- `position` INTEGER
- `created_at` TIMESTAMP WITH TIME ZONE

---

## Flow создания подписки

```
Admin Request (tags, ttl_hours)
    ↓
[Router] → Validates request
    ↓
[Use Case]
    ↓
1. Get active VPN sources by tags → VpnSourceRepository
    ↓
2. Calculate expires_at = now + ttl_hours → TimeProvider
    ↓
3. Create SubscriptionIssue entity
    ↓
4. Generate subscription URL (VPN URIs + TTL metadata)
    ↓
5. Encrypt via HappCryptoAdapter → happ://crypt5/...
    ↓
6. Save SubscriptionIssue + Items to DB
    ↓
[Response] → encrypted_link + metadata
```

---

## Endpoint для обслуживания подписки

Дополнительно нужен endpoint, который HAPP-клиент будет вызывать:

**Router** (`src/presentation/http/subscription_router.py`):
- `GET /api/v1/subscriptions/{public_id}` — получить конфиг подписки
- Без авторизации (public endpoint)

Logic:
- Найти SubscriptionIssue по public_id
- Проверить expires_at (если expired — вернуть 403 Forbidden)
- Проверить status (если revoked — вернуть 403 Forbidden)
- Вернуть текстовый конфиг с VPN URI (по одному на строку)

Response (active):
```
vless://...
trojan://...
vmess://...
```

Response (expired/revoked):
```
HTTP 403 Forbidden
{"detail": "Subscription expired or revoked"}
```

---

## Безопасность

### Что НЕ логируется
- Полные VPN URI
- HAPP encrypted link
- Subscription URL перед шифрованием

### Что логируется
- ID созданной подписки
- Количество VPN источников
- Теги
- TTL
- Fingerprint/hash вместо полного URI

### Токены
- `public_id` — UUID-подобный токен, не секрет, но не predictable
- Генерируется через `uuid4()` или random token generator

---

## Файловая структура

```
src/
  domain/
    subscription_issuance/
      __init__.py
      entities.py
      value_objects.py
      repositories.py
  application/
    subscription_issuance/
      __init__.py
      use_cases.py
      dto.py
  infrastructure/
    db/
      models/
        subscription_issue.py
      repositories/
        subscription_issue.py
    happ/
      __init__.py
      crypto_adapter.py
    subscription/
      __init__.py
      url_generator.py
    time/
      __init__.py
      provider.py
  presentation/
    http/
      subscription_issuance_router.py
      subscription_router.py
      dto/
        subscription_issuance.py
        subscription.py
```

---

## Тесты

### Unit tests
- `test_subscription_issue_entity.py` — entity validation
- `test_happ_crypto_adapter.py` — encryption logic (mock HTTP)
- `test_subscription_url_generator.py` — URL generation
- `test_create_subscription_use_case.py` — use case logic

### Integration tests
- `test_subscription_issuance_endpoints.py` — API tests
- Happy path: create subscription
- Unauthorized: no admin credentials
- Invalid input: empty tags, invalid TTL
- VPN sources not found: no matching tags

---

## Порядок реализации

1. Domain layer: entities, value objects, repository ports
2. Infrastructure: ORM models + миграция
3. Infrastructure: repositories implementation
4. Infrastructure: HAPP crypto adapter
5. Infrastructure: subscription URL generator
6. Application: use case
7. Presentation: admin router + DTO
8. Presentation: subscription serving router
9. Tests

---

## Конфигурация

Добавить в `Settings`:
```python
happ_crypto_api_url: str = "https://crypto.happ.su/api-v2.php"
subscription_base_url: str = "https://your-domain.com"  # базовый URL сервиса
```

Добавить в `.env.example`:
```env
SUBSCRIPTION_BASE_URL=https://your-domain.com
```

---

## Финальные решения

1. **Subscription URL format**: Текстовый список URI сейчас
   - Архитектура должна поддерживать JSON-конфиг в будущем
   - UrlGenerator должен быть расширяемым
   
2. **Expired behavior**: HTTP 403 Forbidden
   - Клиент видит сообщение об ошибке доступа
   
3. **Subscription base URL**: `https://your-domain.com/api/v1/subscriptions/{public_id}`
   - Настраивается через `SUBSCRIPTION_BASE_URL` в .env