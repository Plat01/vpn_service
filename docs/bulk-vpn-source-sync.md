# Массовая синхронизация VPN Sources из Plain Text

## Обзор

Endpoint `PUT /api/v1/admin/vpn-sources/sync-text` позволяет массово загружать, обновлять и синхронизировать VPN-источники из простого текстового формата. Это аналог "замены строк в txt-файле", но с безопасностью для уже выданных подписок.

**Важно:** Endpoint по умолчанию работает в режиме `dry_run=true` (preview) — реальные изменения в БД происходят только при явном указании `dry_run=false`.

---

## Endpoint

```
PUT /api/v1/admin/vpn-sources/sync-text
Authorization: Basic {admin_credentials}
Content-Type: text/plain
```

### Query Parameters

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `dry_run` | bool | `true` | Preview режим: показать что изменится, но не применять |
| `import_group` | string | `default` | Группа источников для раздельного управления |
| `mode` | string | `replace` | Режим синхронизации: `replace`, `upsert`, `append` |
| `deactivate_missing` | bool | `true` | В режиме replace: деактивировать источники, отсутствующие в тексте |
| `ignore_invalid` | bool | `false` | Пропустить невалидные URI или вернуть ошибку |
| `name_strategy` | string | `fragment` | Как определить имя: `fragment`, `host`, `line_number` |
| `tags` | string | — | Список тегов через запятую (например: `main,eu,premium`) |

### Body

Plain text с VPN URI, один URI на строку. Комментарии начинаются с `#`, пустые строки игнорируются.

---

## Формат входного текста

### Базовый пример

```text
# Amsterdam servers
vless://12345678-1234-1234-1234-123456789abc@amsterdam.example.com:443?security=reality#Amsterdam-1
vless://abcd1234-1234-1234-1234-123456789abc@amsterdam.example.com:443?security=reality#Amsterdam-2

# Warsaw backup
trojan://password123@warshaw.example.com:443?security=tls#Warsaw-Backup
```

### Возможности формата

1. **Комментарии**: строки начинающиеся с `#` игнорируются
2. **Пустые строки**: пропускаются
3. **Fragment (#name)**: часть после `#` в URI используется как имя сервера при `name_strategy=fragment`
4. **Максимум 500 строк**: ограничение для безопасности

### Поддерживаемые протоколы

- `vless://` — VLESS protocol
- `vmess://` — VMESS protocol
- `trojan://` — Trojan protocol
- `ss://` — Shadowsocks

---

## Режимы синхронизации

### 1. `replace` (по умолчанию)

Полная замена источников в группе:

- Новые URI → создаются
- Существующие URI → обновляются (имя, теги, `is_active=true`)
- Отсутствующие URI → деактивируются (`is_active=false`) если `deactivate_missing=true`

**Использование:** Полная синхронизация списка серверов из внешнего источника.

**Безопасность:** Деактивация безопасна для подписок — источники просто исключаются из выборки, связи `subscription_issue_items` сохраняются.

```
PUT /api/v1/admin/vpn-sources/sync-text?mode=replace&deactivate_missing=true&dry_run=false
```

### 2. `upsert`

Добавление и обновление без деактивации:

- Новые URI → создаются
- Существующие URI → обновляются
- Старые источники → не изменяются

**Использование:** Добавление новых серверов без влияния на существующие.

```
PUT /api/v1/admin/vpn-sources/sync-text?mode=upsert&dry_run=false
```

### 3. `append`

Только добавление новых:

- Новые URI → создаются
- Существующие URI → пропускаются (не обновляются)
- Старые источники → не изменяются

**Использование:** Безопасное добавление без риска изменить существующие настройки.

```
PUT /api/v1/admin/vpn-sources/sync-text?mode=append&dry_run=false
```

---

## Стратегии именования (`name_strategy`)

### `fragment` (по умолчанию)

Имя берётся из fragment URI (часть после `#`):

```text
vless://uuid@server:443#Amsterdam-1 → name: "Amsterdam-1"
```

Если fragment отсутствует → fallback на `source-{line_number}`.

### `host`

Имя извлекается из hostname:

```text
vless://uuid@amsterdam.example.com:443 → name: "amsterdam.example.com"
```

### `line_number`

Имя генерируется из номера строки:

```text
Строка 5 → name: "source-5"
```

---

## Import Groups (`import_group`)

Позволяют раздельно управлять разными наборами источников.

### Примеры групп

| Группа | Назначение |
|--------|------------|
| `default` | Основные серверы |
| `premium` | Premium подписки |
| `backup` | Резервные серверы |
| `ru` | Российские серверы |
| `eu` | Европейские серверы |

### Использование

```bash
# Синхронизация основной группы
PUT .../sync-text?import_group=default&mode=replace

# Синхронизация premium группы (отдельный список)
PUT .../sync-text?import_group=premium&mode=replace

# Добавление в backup группу
PUT .../sync-text?import_group=backup&mode=append
```

---

## Теги (`tags`)

Теги назначаются всем созданным/обновленным источникам в рамках одной операции.

### Предварительное создание тегов

Перед использованием тегов они должны существовать в системе:

```bash
POST /api/v1/admin/vpn-source-tags
{
  "name": "Europe",
  "slug": "eu"
}
```

### Назначение тегов при синхронизации

```bash
PUT .../sync-text?tags=eu,premium&dry_run=false
```

---

## Dry Run (Preview)

**ВАЖНО:** По умолчанию `dry_run=true` — никаких изменений в БД.

### Preview запрос

```bash
PUT /api/v1/admin/vpn-sources/sync-text?dry_run=true
Content-Type: text/plain

vless://uuid@server:443#Test
```

### Response (preview)

```json
{
  "dry_run": true,
  "mode": "replace",
  "import_group": "default",
  "tags": [],
  "parsed_count": 1,
  "valid_count": 1,
  "invalid_count": 0,
  "to_create_count": 1,
  "to_update_count": 0,
  "to_deactivate_count": 0,
  "created": [],
  "updated": [],
  "deactivated": [],
  "failed": []
}
```

### После подтверждения preview

```bash
PUT .../sync-text?dry_run=false
```

---

## Обработка ошибок

### Невалидные URI

При `ignore_invalid=false` (по умолчанию) невалидный URI вызывает остановку обработки:

```json
{
  "invalid_count": 1,
  "failed": [
    {
      "line": 5,
      "raw": "vless://***MASKED***@***MASKED***",
      "error": "Invalid UUID format: 'test'"
    }
  ]
}
```

### При `ignore_invalid=true`

Невалидные URI пропускаются, валидные обрабатываются:

```bash
PUT .../sync-text?ignore_invalid=true&dry_run=false
```

### Маскирование URI в ответах

URI маскируются в поле `failed[].raw` для безопасности:

```
vless://***MASKED***@***MASKED***
trojan://***MASKED***@***MASKED***
```

**Полные URI** возвращаются в полях `created[].uri` и `updated[].uri`.

---

## Примеры использования

### 1. Полная замена списка серверов (через Swagger UI)

1. Открыть Swagger UI: `/docs`
2. Endpoint: `PUT /api/v1/admin/vpn-sources/sync-text`
3. Authorization: `Basic admin:password`
4. Query params:
   - `dry_run`: сначала `true` для preview
   - `import_group`: `default`
   - `mode`: `replace`
   - `deactivate_missing`: `true`
   - `name_strategy`: `fragment`
5. Body (text/plain):
```text
# Main servers - 2026-04-30
vless://11111111-1111-1111-1111-111111111111@server1.com:443?security=reality#Server1
vless://22222222-2222-2222-2222-222222222222@server2.com:443?security=reality#Server2
vless://33333333-3333-3333-3333-333333333333@server3.com:443?security=reality#Server3
```
6. Проверить preview response
7. Повторить с `dry_run=false`

### 2. Добавление новых серверов без влияния на старые

```bash
PUT .../sync-text?mode=append&import_group=default&dry_run=false

# New backup servers
vless://new-uuid@backup.com:443#Backup1
vless://new-uuid@backup.com:443#Backup2
```

### 3. Синхронизация premium группы с тегами

```bash
# Сначала создать теги
POST /api/v1/admin/vpn-source-tags {"name": "Premium", "slug": "premium"}
POST /api/v1/admin/vpn-source-tags {"name": "Europe", "slug": "eu"}

# Затем синхронизация
PUT .../sync-text?import_group=premium&tags=premium,eu&mode=replace&dry_run=false

vless://uuid@premium1.com:443#Premium-EU-1
vless://uuid@premium2.com:443#Premium-EU-2
```

### 4. curl пример

```bash
curl -X PUT "http://localhost:8000/api/v1/admin/vpn-sources/sync-text?dry_run=false&mode=replace&name_strategy=fragment&import_group=default" \
  -H "Authorization: Basic YWRtaW46cGFzc3dvcmQ=" \
  -H "Content-Type: text/plain" \
  -d "$(cat servers.txt)"
```

---

## История импортов

Каждая операция синхронизации (включая dry_run) записывается в таблицу `vpn_source_imports`:

| Поле | Описание |
|------|----------|
| `id` | UUID операции |
| `import_group` | Группа |
| `mode` | Режим |
| `dry_run` | Флаг preview |
| `total_count` | Всего строк |
| `valid_count` | Валидных |
| `invalid_count` | Невалидных |
| `created_count` | Созданных |
| `updated_count` | Обновленных |
| `deactivated_count` | Деактивированных |
| `failed_count` | Ошибок |
| `created_at` | Время |
| `error_summary` | JSON с деталями ошибок |

---

## Безопасность

### Что безопасно

- ✅ **Деактивация (`is_active=false`)** — источник исключается из подписок, но связи сохраняются
- ✅ **dry_run по умолчанию** — preview перед применением
- ✅ **Маскирование URI в логах** — секреты не попадают в logs
- ✅ **Максимум 500 строк** — защита от огромных payloads

### Что НЕ безопасно

- ❌ **Физический DELETE** — разрушает связи `subscription_issue_items`
- ❌ **Прямое удаление из БД** — используйте только деактивацию через sync

### Рекомендации

1. Всегда начинать с `dry_run=true`
2. Проверять `to_deactivate_count` в preview
3. Использовать `import_group` для раздельного управления
4. Хранить backup текстового списка перед sync

---

## Ограничения

| Ограничение | Значение |
|-------------|----------|
| Максимум строк | 500 |
| Длина import_group | 1-100 символов |
| Теги должны существовать | Да (или пусто) |
| URI формат | vless, vmess, trojan, ss |

---

## Response Schema

```json
{
  "dry_run": bool,
  "mode": "replace|upsert|append",
  "import_group": string,
  "tags": [string],
  "parsed_count": int,
  "valid_count": int,
  "invalid_count": int,
  "to_create_count": int,
  "to_update_count": int,
  "to_deactivate_count": int,
  "created": [
    {
      "id": UUID,
      "name": string,
      "uri": string,
      "action": "create",
      "tags": [{ "id", "name", "slug", "created_at" }]
    }
  ],
  "updated": [similar],
  "deactivated": [similar],
  "failed": [
    {
      "line": int,
      "raw": string (masked),
      "error": string
    }
  ]
}
```

---

## Troubleshooting

### "Ссылки не добавляются"

Проверьте `dry_run` — по умолчанию `true`. Установите `dry_run=false`.

### "Invalid UUID format"

UUID в vless URI должен быть валидным format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.

### "Tag not found"

Теги должны быть созданы заранее через `POST /api/v1/admin/vpn-source-tags`.

### "Too many lines: max 500"

Разделите список на части или уменьшите количество строк.

---

## FAQ

**Q: Что происходит с подписками при деактивации источника?**
A: Источник просто исключается из выборки при следующих запросах подписки. Уже выданные подписки сохраняют связь, но деактивированный источник не попадёт в новые.

**Q: Можно ли восстановить деактивированный источник?**
A: Да. Include его в следующий sync с `mode=replace` или `upsert`, или обновите через `PATCH /vpn-sources/{id}` с `is_active=true`.

**Q: Как удалить источник permanently?**
A: НЕ рекомендуется. Используйте деактивацию. Physical DELETE разрушает историю подписок.

**Q: Как проверить что изменилось?**
A: Используйте `dry_run=true` сначала. Response покажет `to_create_count`, `to_update_count`, `to_deactivate_count`.

**Q: Сколько URI можно загрузить за раз?**
A: Максимум 500 строк. Для больших списков — разделить на части или несколько вызовов.

---

## Замена устаревших VPN источников

### Сценарий

Когда старый VPN URI перестает работать (сервер недоступен, ключ устарел, протокол изменился), нужно заменить его на новый, сохранив правильную работу подписок.

### Как работает замена

**Важно:** Подписки хранят связь с источниками через `vpn_source_id`, не через URI. Это означает:

- ✅ Деактивация старого источника — подписки автоматически исключают его из выборки
- ✅ Новый источник с тем же тегом — подписки автоматически включают его
- ❌ Физическое удаление — разрушает историю и связи, НЕ делать

### Процесс замены через sync-text

#### Шаг 1: Подготовка нового списка

Создайте текстовый файл с **новыми** URI (без старых):

```text
# New servers - replacing old Amsterdam nodes
vless://NEW-UUID-1111-1111-1111-111111111111@new-server1.com:443?security=reality#Amsterdam-New-1
vless://NEW-UUID-2222-2222-2222-222222222222@new-server2.com:443?security=reality#Amsterdam-New-2

# Keep working servers
vless://old-working-uuid@working-server.com:443?security=reality#Working-Server
```

#### Шаг 2: Preview с dry_run

```bash
PUT /api/v1/admin/vpn-sources/sync-text?dry_run=true&mode=replace&import_group=default&tags=main
```

Проверьте:
- `to_create_count` — новые серверы
- `to_deactivate_count` — старые серверы (которые не в списке)

#### Шаг 3: Apply с dry_run=false

```bash
PUT /api/v1/admin/vpn-sources/sync-text?dry_run=false&mode=replace&import_group=default&tags=main&deactivate_missing=true
```

Результат:
- Новые URI → созданы с `is_active=true`
- Старые URI (не в списке) → `is_active=false`
- Работающие URI (в списке) → обновлены, остаются `is_active=true`

### Влияние на подписки

| Ситуация | Результат для подписки |
|----------|------------------------|
| Старый источник деактивирован | Исключается из новых запросов подписки |
| Новый источник добавлен с тем же тегом | Автоматически попадает в подписки с этим тегом |
| Подписка уже выдана | Старый источник в ней сохраняется (история), но при обновлении — исключается |

### Пример: Полная замена группы Amsterdam

#### Старые источники в БД:

```
vless://OLD-UUID-1@amsterdam-old.com:443#Amsterdam-1 (is_active=true, tags=[main, eu])
vless://OLD-UUID-2@amsterdam-old.com:443#Amsterdam-2 (is_active=true, tags=[main, eu])
vless://WORKING-UUID@paris.com:443#Paris-1 (is_active=true, tags=[main, eu])
```

#### Новый текст для sync:

```text
# Replaced Amsterdam servers
vless://NEW-UUID-1@amsterdam-new.com:443#Amsterdam-New-1
vless://NEW-UUID-2@amsterdam-new.com:443#Amsterdam-New-2

# Keep working Paris
vless://WORKING-UUID@paris.com:443#Paris-1
```

#### После sync (mode=replace, import_group=default, tags=main,eu):

```
vless://OLD-UUID-1@... → is_active=false (deactivated)
vless://OLD-UUID-2@... → is_active=false (deactivated)
vless://NEW-UUID-1@... → is_active=true, tags=[main, eu] (created)
vless://NEW-UUID-2@... → is_active=true, tags=[main, eu] (created)
vless://WORKING-UUID@paris.com:443 → is_active=true, tags=[main, eu] (updated)
```

#### Результат для подписок:

При следующем запросе подписки с тегами `main,eu`:
- Amsterdam-New-1 ✅ включён
- Amsterdam-New-2 ✅ включён
- Paris-1 ✅ включён
- Amsterdam-Old ❌ исключён (is_active=false)

### Альтернатива: Обновление конкретного источника

Если нужно заменить только один URI, а не всю группу:

```bash
PATCH /api/v1/admin/vpn-sources/{vpn_source_id}
{
  "uri": "vless://NEW-UUID@new-server.com:443?security=reality",
  "name": "Amsterdam-Replaced"
}
```

**Результат:** URI обновляется, подписки используют новый URI при следующем запросе.

**Плюсы:** Не нужно sync, сохраняется связь с подписками.

**Минусы:** UUID источника не меняется, если нужно другой UUID — используйте sync.

### Восстановление деактивированного источника

Если старый сервер снова работает:

```bash
# Через sync - добавить обратно
PUT .../sync-text?mode=upsert

vless://OLD-UUID-1@amsterdam-old.com:443#Amsterdam-Restored

# Или напрямую
PATCH /api/v1/admin/vpn-sources/{id}
{
  "is_active": true
}
```

### Рекомендации по замене

| Сценарий | Метод |
|----------|-------|
| Массовая замена устаревших серверов | `sync-text` с `mode=replace` |
| Замена одного сервера на новый | `PATCH /vpn-sources/{id}` с новым `uri` |
| Добавление новых без удаления старых | `sync-text` с `mode=append` или `mode=upsert` |
| Временное отключение проблемного сервера | `PATCH /vpn-sources/{id}` с `is_active=false` |

### Проверка после замены

```bash
GET /api/v1/admin/vpn-sources?is_active=true&tags=main

# Проверить что:
# 1. Новые серверы присутствуют с is_active=true
# 2. Старые серверы отсутствуют или is_active=false
# 3. Теги назначены правильно
```