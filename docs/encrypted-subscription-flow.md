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
  "tags": ["bypass"],
  "ttl_hours": 24,
  "max_devices": null
}
```

- `tags` — список тегов для выбора VPN источников (минимум 1 тег)
- `ttl_hours` — срок действия подписки в часах (1-8760, max 1 год)
- `max_devices` — ограничение устройств (optional, для будущего расширения)

**Response:**
```json
{
  "id": "uuid",
  "public_id": "uuid-string",
  "encrypted_link": "happ://crypt5/...",
  "expires_at": "2026-04-25T12:00:00Z",
  "vpn_sources_count": 2,
  "tags_used": ["bypass"],
  "created_at": "2026-04-24T12:00:00Z"
}
```

---

### 4. Получение конфига подписки (публичный endpoint)

**Endpoint:** `GET /api/v1/subscriptions/{public_id}`

**Авторизация:** Не требуется (публичный)

**Response (active):**
```
vless://uuid@server1:443?...
vless://uuid@server2:443?...
trojan://password@server3:443?...
```

Текстовый список VPN URI, по одному на строку.

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

# 3. Создать зашифрованную подписку
curl -X POST https://vpn.example.com/api/v1/admin/subscriptions/encrypted \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"tags": ["premium"], "ttl_hours": 72}'

# Response содержит encrypted_link:
# "happ://crypt5/..."

# 4. Проверить подписку (публичный endpoint)
curl https://vpn.example.com/api/v1/subscriptions/{public_id}

# Response:
# vless://...
# trojan://...
```

---

## Безопасность

### Что НЕ логируется

- Полные VPN URI
- HAPP encrypted link
- Subscription URL перед шифрованием
- Полные request body с VPN URI

### Что логируется

- ID созданной подписки
- Количество VPN источников
- Теги
- TTL
- Fingerprint/hash вместо полных URI

### TTL защита

- TTL проверяется на сервере при каждом запросе подписки
- Expired подписки возвращают HTTP 403
- HAPP не имеет встроенного TTL — контроль полностью на сервере