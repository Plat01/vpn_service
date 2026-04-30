# Создание зашифрованной HAPP-подписки

## Обзор

Сервис создаёт HAPP-совместимые зашифрованные ссылки на подписку. Подписка содержит список VPN URI, выбранных по тегам, с ограниченным сроком действия (TTL).

## Эндпоинты

### 1. Создание тегов

**Endpoint:** `POST /api/v1/admin/vpn-source-tags`

**Авторизация:** HTTP Basic Auth (admin credentials)

**Request:**
```json
{
  "name": "Europe",
  "slug": "eu"
}
```

- `name` — отображаемое название тега (1-100 символов)
- `slug` — уникальный идентификатор тега для фильтрации (1-100 символов, lowercase, alphanumeric + `-` + `_`)
- Если `slug` не указан, генерируется автоматически из `name`

**Response:**
```json
{
  "id": "uuid",
  "name": "Europe",
  "slug": "eu",
  "created_at": "2026-04-24T12:00:00Z"
}
```

---

### 2. Загрузка VPN источников

**Endpoint:** `POST /api/v1/admin/vpn-sources`

**Авторизация:** HTTP Basic Auth

**Request:**
```json
{
  "name": "EU Server 1",
  "uri": "vless://uuid@server:443?type=tcp&security=reality&...",
  "description": "Optional description",
  "is_active": true,
  "tags": ["eu", "premium"]
}
```

- `name` — название сервера (1-255 символов)
- `uri` — VPN URI в формате `vless://`, `trojan://`, `vmess://` и др.
- `description` — необязательное описание
- `is_active` — активность источника (по умолчанию `true`)
- `tags` — список тегов (slug) для группировки

**Response:**
```json
{
  "id": "uuid",
  "name": "EU Server 1",
  "uri": "vless://...",
  "description": null,
  "is_active": true,
  "tags": [
    {"id": "uuid", "name": "Europe", "slug": "eu", "created_at": "..."}
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

---

### 3. Создание зашифрованной подписки

**Endpoint:** `POST /api/v1/admin/subscriptions/encrypted`

**Авторизация:** HTTP Basic Auth

**Request:**
```json
{
  "tags": ["bypass", "premium"],
  "ttl_hours": 8,
  "max_devices": 1,
  "metadata": {
    "profile_title": "OvalVPN",
    "profile_update_interval": 1,
    "support_url": "https://t.me/OvalVPN_Bot",
    "profile_web_page_url": "https://t.me/OvalVPN_Bot",
    "announce": "OvalVPN – включил и забыл. Неограниченный трафик.",
    "traffic_info": {
      "upload": 0,
      "download": 0,
      "total": 524288000
    },
    "info_block": {
      "color": "blue",
      "text": "Для продления подписки обратитесь в поддержку",
      "button_text": "Поддержка",
      "button_link": "https://t.me/OvalVPN_Bot"
    },
    "expire_notification": {
      "enabled": true,
      "button_link": "https://t.me/OvalVPN_Bot"
    }
  },
  "behavior": {
    "autoconnect": true,
    "autoconnect_type": "lowestdelay",
    "ping_on_open": true,
    "fallback_url": "https://backup.example.com/sub/{public_id}"
  },
  "provider_id": null
}
```

#### Основные параметры

- `tags` — список тегов для выбора VPN источников (минимум 1 тег)
- `ttl_hours` — срок действия подписки в часах (1-8760, max 1 год)
- `max_devices` — ограничение устройств (optional, null = без ограничений)

#### Metadata параметры (HAPP заголовки)

- `profile_title` — название профиля в HAPP (max 25 символов)
- `profile_update_interval` — интервал обновления в часах (min 1)
- `support_url` — URL поддержки
- `profile_web_page_url` — URL web-страницы профиля
- `announce` — текст объявления (max 200 символов, русский текст автоматически base64-encoded)
- `traffic_info` — информация о трафике:
  - `upload` — uploaded bytes (default 0)
  - `download` — downloaded bytes (default 0)
  - `total` — total traffic limit in bytes (500MB = 524288000)
- `info_block` — информационный блок:
  - `color` — цвет ("red", "blue", "green")
  - `text` — текст (max 200 символов)
  - `button_text` — текст кнопки (max 25 символов)
  - `button_link` — URL кнопки
- `expire_notification` — уведомление об окончании:
  - `enabled` — включить уведомление (boolean)
  - `button_link` — URL кнопки при окончании

#### Behavior параметры

- `autoconnect` — авто-подключение при запуске (boolean)
- `autoconnect_type` — тип авто-подключения ("lastused" или "lowestdelay")
- `ping_on_open` — ping при открытии приложения (boolean)
- `fallback_url` — fallback URL при ошибке (placeholder `{public_id}` заменяется автоматически)

#### Provider ID

- `provider_id` — ID провайдера для расширенных функций HAPP (optional)

**Response:**
```json
{
  "id": "uuid",
  "public_id": "uuid-string",
  "encrypted_link": "happ://crypt5/...",
  "expires_at": "2026-04-25T06:00:00Z",
  "vpn_sources_count": 2,
  "tags_used": ["bypass", "premium"],
  "created_at": "2026-04-24T22:00:00Z"
}
```

---

### 4. Получение конфига подписки (публичный endpoint)

**Endpoint:** `GET /api/v1/subscriptions/{public_id}`

**Авторизация:** Не требуется (публичный)

**Response (active):**
```
#profile-title: OvalVPN
#profile-update-interval: 1
#subscription-userinfo: upload=0; download=0; total=524288000; expire=1777099803
#support-url: https://t.me/OvalVPN_Bot
#profile-web-page-url: https://t.me/OvalVPN_Bot
#announce: base64:T3ZhbFZQTiDigJMg0LLQutC70Y7Rh9C40Lsg0Lgg0LfQsNCx0YvQuy4u
#sub-info-color: blue
#sub-info-text: Для продления подписки обратитесь в поддержку
#sub-info-button-text: Поддержка
#sub-info-button-link: https://t.me/OvalVPN_Bot
#sub-expire: 1
#sub-expire-button-link: https://t.me/OvalVPN_Bot
#subscription-autoconnect: true
#subscription-autoconnect-type: lowestdelay
#subscription-ping-onopen-enabled: true

vless://uuid@server1:443?...#Server Name 1
vless://uuid@server2:443?...#Server Name 2
```

VPN URI включают name как fragment (`#name`). Если исходный URI содержал fragment, он заменяется на name из базы.

**HAPP заголовки автоматически генерируются:**
- `#subscription-userinfo` — включает `expire` из TTL
- `#announce` — русский текст base64-encoded
- Все metadata/behavior поля преобразуются в HAPP заголовки

**Response (expired/revoked):**
```
HTTP 403 Forbidden
{"detail": "Subscription expired"}
```

---

## Процесс создания подписки

### Шаги выполнения

1. **Поиск VPN источников**
   - Сервис ищет активные VPN источники с указанными тегами
   - Если источников нет → HTTP 400 Bad Request

2. **Создание SubscriptionIssue**
   - Генерируется `public_id` (UUID4)
   - Вычисляется `expires_at` = now + ttl_hours
   - Создается entity со статусом `active`

3. **Создание SubscriptionIssueItems**
   - Для каждого найденного VPN источника создается item с position

4. **Генерация subscription URL**
   - URL: `{SUBSCRIPTION_BASE_URL}/api/v1/subscriptions/{public_id}`
   - `SUBSCRIPTION_BASE_URL` должен быть публично доступным из интернета

5. **Шифрование через HAPP API**
   - POST запрос на `{HAPP_CRYPTO_API_URL}`
   - Payload: `{"url": subscription_url}`
   - Response: `{"encrypted_link": "happ://crypt5/..."}`

6. **Сохранение encrypted_link**
   - Обновление SubscriptionIssue с зашифрованной ссылкой

7. **Возврат результата**
   - Клиент получает `encrypted_link` для использования в HAPP приложении

---

## Расшифровка HAPP-ссылки

### Как HAPP приложение работает с ссылкой

1. **Расшифровка**
   - HAPP приложение получает `happ://crypt5/...`
   - Расшифровывает → получает subscription URL
   - URL: `https://your-domain.com/api/v1/subscriptions/{public_id}`

2. **Запрос конфига**
   - HAPP делает GET запрос на subscription URL
   - Сервис проверяет TTL и статус подписки

3. **Проверка TTL**
   - Если `expires_at < now` → HTTP 403 Forbidden
   - Если статус `revoked` → HTTP 403 Forbidden
   - Если active → возвращается список VPN URI

4. **Использование VPN**
   - HAPP приложение парсит полученные VPN URI
   - Подключается к VPN серверам

---

## Требования для работы

### Переменные окружения

| Variable | Description | Example |
|----------|-------------|---------|
| `SUBSCRIPTION_BASE_URL` | Публичный URL сервиса | `https://vpn.example.com` |
| `HAPP_CRYPTO_API_URL` | HAPP API endpoint | `https://crypto.happ.su/api-v2.php` |

### Важно

- `SUBSCRIPTION_BASE_URL` должен быть **публично доступным** из интернета
- HAPP API обращается к этому URL для проверки подписки
- localhost или внутренние URL не будут работать

---

## Пример полного flow

```bash
# 1. Создать тег
curl -X POST https://vpn.example.com/api/v1/admin/vpn-source-tags \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"name": "Premium", "slug": "premium"}'

# 2. Загрузить VPN источники
curl -X POST https://vpn.example.com/api/v1/admin/vpn-sources \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"name": "Server 1", "uri": "vless://...", "tags": ["premium"]}'

curl -X POST https://vpn.example.com/api/v1/admin/vpn-sources \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"name": "Server 2", "uri": "trojan://...", "tags": ["premium"]}'

# 3. Создать зашифрованную подписку с HAPP metadata
curl -X POST https://vpn.example.com/api/v1/admin/subscriptions/encrypted \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["premium"],
    "ttl_hours": 72,
    "max_devices": 1,
    "metadata": {
      "profile_title": "My VPN",
      "profile_update_interval": 1,
      "support_url": "https://t.me/support_bot",
      "traffic_info": {
        "total": 10737418240
      },
      "info_block": {
        "color": "blue",
        "text": "Contact support for renewal",
        "button_text": "Support",
        "button_link": "https://t.me/support_bot"
      },
      "expire_notification": {
        "enabled": true
      }
    },
    "behavior": {
      "autoconnect": true,
      "autoconnect_type": "lowestdelay"
    }
  }'

# Response содержит encrypted_link:
# "happ://crypt5/..."

# 4. Проверить подписку (публичный endpoint)
curl https://vpn.example.com/api/v1/subscriptions/{public_id}

# Response:
# #profile-title: My VPN
# #profile-update-interval: 1
# #subscription-userinfo: upload=0; download=0; total=10737418240; expire=...
# #support-url: https://t.me/support_bot
# #sub-info-color: blue
# #sub-info-text: Contact support for renewal
# #sub-info-button-text: Support
# #sub-info-button-link: https://t.me/support_bot
# #sub-expire: 1
# #subscription-autoconnect: true
# #subscription-autoconnect-type: lowestdelay
#
# vless://...
# trojan://...
```

---

## HAPP заголовки (автоматически генерируются)

Сервис автоматически генерирует HAPP заголовки из metadata/behavior:

| Metadata field | HAPP header | Example |
|----------------|-------------|---------|
| `profile_title` | `#profile-title` | `#profile-title: OvalVPN` |
| `profile_update_interval` | `#profile-update-interval` | `#profile-update-interval: 1` |
| `traffic_info` + TTL | `#subscription-userinfo` | `upload=0; download=0; total=524288000; expire=1777099803` |
| `support_url` | `#support-url` | `#support-url: https://t.me/bot` |
| `profile_web_page_url` | `#profile-web-page-url` | `#profile-web-page-url: https://t.me/bot` |
| `announce` (русский) | `#announce: base64:...` | Автоматически base64-encoded |
| `info_block.color` | `#sub-info-color` | `#sub-info-color: blue` |
| `info_block.text` | `#sub-info-text` | `#sub-info-text: Text` |
| `expire_notification.enabled` | `#sub-expire` | `#sub-expire: 1` |

| Behavior field | HAPP header | Example |
|----------------|-------------|---------|
| `autoconnect` | `#subscription-autoconnect` | `#subscription-autoconnect: true` |
| `autoconnect_type` | `#subscription-autoconnect-type` | `#subscription-autoconnect-type: lowestdelay` |
| `ping_on_open` | `#subscription-ping-onopen-enabled` | `#subscription-ping-onopen-enabled: true` |
| `fallback_url` | `#fallback-url` | `#fallback-url: https://backup.com/sub/{public_id}` |

| Provider | HAPP header | Example |
|----------|-------------|---------|
| `provider_id` | `#providerid` | `#providerid PROVIDER_123` |

**Примечание:** `{public_id}` в `fallback_url` автоматически заменяется на реальный public_id подписки.

---

## Безопасность

### Что НЕ логируется

- Полные VPN URI
- HAPP encrypted link
- Subscription URL перед шифрованием
- Полные request body с VPN URI
- Полные metadata (profile_title, support_url, announce могут быть чувствительными)
- Provider ID
- Fallback URL с public_id

### Что логируется

- ID созданной подписки
- Количество VPN источников
- Теги
- TTL
- Fingerprint/hash вместо полных URI
- Metadata presence: `metadata present: true/false`
- Metadata fields count: `metadata fields count: 5`

### TTL защита

- TTL проверяется на сервере при каждом запросе подписки
- Expired подписки возвращают HTTP 403
- HAPP не имеет встроенного TTL — контроль полностью на сервере

### Metadata безопасность

- Metadata не используется для бизнес-логики, только для display
- Русский текст в `announce` автоматически base64-encoded
- `fallback_url` placeholder `{public_id}` заменяется безопасно
- Metadata хранится в JSONB, что позволяет гибко добавлять новые HAPP fields без миграций

---

## Архитектура

### Хранение metadata/behavior

- **JSONB columns**: `metadata`, `behavior`, `provider_id` хранятся в `subscription_issues` таблице
- **Value Objects**: Domain layer использует frozen dataclasses с валидацией
- **Автоматическая генерация**: HAPP заголовки генерируются при запросе конфига

### Layers

```
Domain Layer (value objects):
  src/domain/subscription_issuance/value_objects.py
  - TrafficInfo, InfoBlock, ExpireNotification
  - SubscriptionMetadata, SubscriptionBehavior

Infrastructure Layer:
  src/infrastructure/subscription/happ_metadata_generator.py
  - HappMetadataGenerator (HAPP headers generation)
  
  src/infrastructure/subscription/url_generator.py
  - TextListConfigGenerator (config with headers + VPN URIs)
  
  src/infrastructure/db/repositories/subscription_issue.py
  - Mapping: JSONB <-> Domain Value Objects

Presentation Layer:
  src/presentation/http/dto/subscription_issuance.py
  - HTTP request/response DTOs
  
  src/presentation/http/subscription_issuance_router.py
  - Request -> Domain Value Objects conversion
```

### Future considerations

1. **OAuth2/OIDC**: Metadata может связываться с user profile (personal announce)
2. **Personal cabinet**: User может редактировать свой `profile_title`, `announce`
3. **Analytics**: Tracking ID в behavior для статистики
4. **A/B testing**: Different metadata templates для testing UX