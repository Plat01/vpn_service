# Управление подписками: создание, просмотр и удаление

## Обзор

Подписка — это выданный токен доступа к набору VPN-серверов, подобранных по тегам. После создания возвращается зашифрованная HAPP-ссылка. Подписка имеет срок действия (TTL) и опциональное ограничение по количеству устройств.

---

## 1. Создание подписки

### 1.1. Через API (стандартный способ)

**Endpoint:** `POST /api/v1/admin/subscriptions/encrypted`

**Авторизация:** HTTP Basic Auth (bootstrap, временно)

**Процесс:**
1. Сервис находит все активные VPN-источники с указанными тегами
2. Создаёт `SubscriptionIssue` со статусом `active`
3. Формирует ссылку на конфиг вида `{SUBSCRIPTION_BASE_URL}/api/v1/subscriptions/{public_id}`
4. Шифрует ссылку через внешний HAPP Crypto API
5. Возвращает зашифрованную HAPP-ссылку

**Request:**
```json
{
  "tags": ["bypass", "premium"],
  "ttl_hours": 8,
  "max_devices": 1,
  "metadata": {
    "profile_title": "My VPN",
    "profile_update_interval": 1,
    "support_url": "https://t.me/support_bot",
    "profile_web_page_url": "https://t.me/support_bot",
    "announce": "Добро пожаловать",
    "traffic_info": {
      "upload": 0,
      "download": 0,
      "total": 524288000
    },
    "info_block": {
      "color": "blue",
      "text": "Для продления обратитесь в поддержку",
      "button_text": "Поддержка",
      "button_link": "https://t.me/support_bot"
    },
    "expire_notification": {
      "enabled": true,
      "button_link": "https://t.me/support_bot"
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

**Response (201 Created):**
```json
{
  "id": "uuid",
  "public_id": "uuid-string",
  "encrypted_link": "happ://crypt5/...",
  "expires_at": "2026-04-25T06:00:00Z",
  "vpn_sources_count": 3,
  "tags_used": ["bypass", "premium"],
  "created_at": "2026-04-24T22:00:00Z"
}
```

`encrypted_link` — это готовая ссылка для HAPP-совместимого приложения. Приложение расшифровывает ссылку и получает URL конфига, по которому скачивает список VPN-серверов.

#### curl пример

```bash
curl -X POST "http://localhost:8000/api/v1/admin/subscriptions/encrypted" \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["bypass"],
    "ttl_hours": 24,
    "max_devices": 1,
    "metadata": {
      "profile_title": "My VPN",
      "profile_update_interval": 8
    }
  }'
```

---

### 1.2. Минимальный запрос (только обязательные поля)

Обязательны только `tags` (минимум 1 тег) и `ttl_hours`. Всё остальное опционально:

```json
{
  "tags": ["bypass"],
  "ttl_hours": 24
}
```

При таком запросе HAPP-заголовки не генерируются (кроме базового `#subscription-userinfo` с TTL).

---

## 2. Просмотр подписки (публичный конфиг)

**Endpoint:** `GET /api/v1/subscriptions/{public_id}`

**Авторизация:** Не требуется

**Динамический состав:** В отличие от момента создания, при каждом запросе конфиг собирается динамически — сервис выбирает все активные VPN-источники по тем тегам, с которыми подписка была выпущена. Добавление нового источника в тег автоматически добавляет его во все подписки с этим тегом. Удаление или деактивация источника убирает его из всех подписок.

Возвращает plain text конфиг с HAPP-заголовками и списком VPN URI в формате:

```
#profile-title: My VPN
#profile-update-interval: 1
#subscription-userinfo: upload=0; download=0; total=524288000; expire=1777099803
#support-url: https://t.me/support_bot
#profile-web-page-url: https://t.me/support_bot

vless://uuid@server1:443?type=tcp&security=reality&... #Server Name 1
vless://uuid@server2:443?type=tcp&security=reality&... #Server Name 2
```

Если подписка истекла или отозвана — возвращается `HTTP 403 Forbidden` с телом, содержащим "отравленный" конфиг с одним фиктивным сервером. HAPP-приложение перезаписывает локальный кеш, и старые рабочие серверы исчезают.

#### curl пример

```bash
curl "http://localhost:8000/api/v1/subscriptions/{public_id}"
```

---

## 3. Удаление / отзыв подписки

### 3.1. Текущая возможность (revoke)

На данный момент API-эндпоинта для отзыва подписки нет. Отзыв доступен только через прямую работу с сущностью `SubscriptionIssue`:

```python
subscription.revoke(revoked_at=now)
await subscription_repo.update(subscription)
```

После отзыва:
- Статус меняется на `revoked`
- Публичный endpoint начинает возвращать `403 Forbidden` с "отравленным" конфигом
- Связи `subscription_issue_items` сохраняются (история не теряется)

### 3.2. Удаление из БД (не рекомендуется)

Физическое удаление строк из `subscription_issues` и `subscription_issue_items` **не рекомендуется**, так как:
- Теряется аудит: когда и кому была выдана подписка
- Теряется связь с VPN-источниками
- Невозможно расследовать инциденты безопасности

Используйте отзыв (revoke) вместо DELETE.

### 3.3. Запланированный API для отзыва

В будущем планируется endpoint:

```
PATCH /api/v1/admin/subscriptions/{public_id}/revoke
Authorization: Basic ...

Response: 200 OK
{
  "public_id": "uuid-string",
  "status": "revoked",
  "revoked_at": "2026-04-25T12:00:00Z"
}
```

Для отслеживания статуса реализации смотрите issues проекта.

---

## 4. Параметры подписки

| Параметр | Обязательный | Описание |
|----------|-------------|----------|
| `tags` | Да | Список тегов для выборки VPN-источников (минимум 1) |
| `ttl_hours` | Да | Срок действия в часах (1–8760, макс 1 год) |
| `max_devices` | Нет | Лимит устройств (сейчас хранится, но не enforced) |
| `metadata` | Нет | HAPP-заголовки (profile_title, announce, и т.д.) |
| `behavior` | Нет | HAPP-поведение (autoconnect, fallback_url, и т.д.) |
| `provider_id` | Нет | HAPP provider ID |

---

## 5. Безопасность

- `encrypted_link` не логируется целиком (логируется только длина)
- `public_id` маскируется в логах (`public_id[:8] + "..."`)
- Полный subscription URL нелогируется
- При ошибках валидации URI маскируются (`vless://***MASKED***@***MASKED***`)
- Подписка проверяется на сервере при КАЖДОМ запросе (не доверяй клиенту)
- Expired/revoked подписки возвращают `403` с "отравленным" конфигом

---

## 6. Жизненный цикл подписки

```
Создание (active) ──────────────────────────────────────────────┐
      │                                                         │
      ├── Достигнут expires_at → expired (403 при запросе)      │
      │                                                         │
      ├── Отзыв (revoke) → revoked (403 при запросе)            │
      │                                                         │
      └── Активна → нормальная выдача конфига (200)             │
                                                                │
  Любой запрос проверяет TTL → auto-expire если просрочена      │
```

После истечения или отзыва подписка остаётся в БД для аудита. Новые подписки с теми же тегами будут включать актуальные VPN-источники. Существующие подписки также динамически получают актуальный набор источников при каждом запросе конфига.
