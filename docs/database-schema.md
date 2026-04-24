# Схема базы данных для подписок

## Таблицы

### vpn_sources

Хранит исходные VPN URI и их метаданные.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(255) | Название источника |
| `uri` | TEXT | VPN URI (`vless://`, `trojan://`, etc.) |
| `description` | TEXT | Описание (optional) |
| `is_active` | BOOLEAN | Активность источника |
| `created_at` | TIMESTAMP WITH TIME ZONE | Дата создания |
| `updated_at` | TIMESTAMP WITH TIME ZONE | Дата последнего обновления |

**Indexes:**
- `idx_vpn_sources_is_active` — фильтрация по активности

---

### vpn_source_tags

Теги для группировки VPN источников.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(100) | Название тега |
| `slug` | VARCHAR(100) | Уникальный идентификатор (lowercase) |
| `created_at` | TIMESTAMP WITH TIME ZONE | Дата создания |

**Indexes:**
- `idx_vpn_source_tags_slug` — unique index для slug

---

### vpn_source_tag_associations

Связь VPN источников с тегами (many-to-many).

| Column | Type | Description |
|--------|------|-------------|
| `vpn_source_id` | UUID | FK → vpn_sources.id |
| `tag_id` | UUID | FK → vpn_source_tags.id |

**Indexes:**
- `idx_vpn_source_tag_assoc_source` — индекс по vpn_source_id
- `idx_vpn_source_tag_assoc_tag` — индекс по tag_id

---

### subscription_issues

Выданные подписки.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `public_id` | VARCHAR(36) | Токен для URL подписки (UUID4) |
| `status` | VARCHAR(20) | Статус: `active`, `expired`, `revoked` |
| `expires_at` | TIMESTAMP WITH TIME ZONE | Срок действия |
| `max_devices` | INTEGER | Лимит устройств (optional) |
| `created_at` | TIMESTAMP WITH TIME ZONE | Дата создания |
| `created_by` | VARCHAR(255) | Кто создал (admin username) |
| `tags_used` | TEXT[] | Snapshot тегов для выбора VPN |
| `encrypted_link` | TEXT | HAPP зашифрованная ссылка |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | Дата отзыва (если revoked) |

**Indexes:**
- `idx_subscription_issues_public_id` — unique index
- `idx_subscription_issues_status` — фильтрация по статусу
- `idx_subscription_issues_expires_at` — фильтрация по сроку действия

---

### subscription_issue_items

VPN источники, включённые в подписку.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `subscription_issue_id` | UUID | FK → subscription_issues.id |
| `vpn_source_id` | UUID | FK → vpn_sources.id |
| `position` | INTEGER | Порядок в списке |
| `created_at` | TIMESTAMP WITH TIME ZONE | Дата создания |

**Indexes:**
- `idx_subscription_issue_items_subscription_issue_id` — связь с подпиской
- `idx_subscription_issue_items_vpn_source_id` — связь с VPN источником

---

## ER Diagram

```
vpn_source_tags
    │
    │ (many-to-many via vpn_source_tag_associations)
    │
vpn_sources ←── subscription_issue_items ──→ subscription_issues
    │                      │                        │
    │                      │                        │
    └                      └                        └
```

---

## Жизненный цикл данных

### Создание VPN источника

1. POST `/vpn-sources` → запись в `vpn_sources`
2. Теги → записи в `vpn_source_tags` (если новые)
3. Связи → записи в `vpn_source_tag_associations`

### Создание подписки

1. POST `/subscriptions/encrypted`
2. Поиск VPN по тегам → JOIN `vpn_sources` + `vpn_source_tag_associations` + `vpn_source_tags`
3. Запись в `subscription_issues`:
   - `public_id` = UUID4 (генерируется)
   - `status` = `active`
   - `expires_at` = now + ttl_hours
   - `tags_used` = snapshot тегов запроса
4. Запись в `subscription_issue_items`:
   - Для каждого найденного VPN источника
   - `position` = порядковый номер
5. HAPP шифрование → `encrypted_link`
6. Update `subscription_issues.encrypted_link`

### Запрос подписки (GET /subscriptions/{public_id})

1. SELECT `subscription_issues` WHERE `public_id` = ?
2. Проверка TTL: если `expires_at < now` → `status = expired`
3. SELECT `subscription_issue_items` WHERE `subscription_issue_id` = ?
4. Для каждого item: SELECT `vpn_sources` WHERE `id` = vpn_source_id AND `is_active` = true
5. Возврат списка URI

---

## Пример данных

### vpn_sources

| id | name | uri | is_active |
|----|------|-----|-----------|
| uuid-1 | RU Server 1 | vless://... | true |
| uuid-2 | RU Server 2 | vless://... | true |
| uuid-3 | EU Server 1 | trojan://... | true |

### vpn_source_tags

| id | name | slug |
|----|------|------|
| tag-1 | Russia | ru |
| tag-2 | Bypass | bypass |

### vpn_source_tag_associations

| vpn_source_id | tag_id |
|---------------|--------|
| uuid-1 | tag-1 |
| uuid-1 | tag-2 |
| uuid-2 | tag-1 |
| uuid-2 | tag-2 |
| uuid-3 | tag-2 |

### subscription_issues

| id | public_id | status | expires_at | tags_used | encrypted_link |
|----|-----------|--------|------------|-----------|----------------|
| sub-1 | pub-uuid | active | 2026-04-25 | ["bypass"] | happ://crypt5/... |

### subscription_issue_items

| id | subscription_issue_id | vpn_source_id | position |
|----|------------------------|---------------|----------|
| item-1 | sub-1 | uuid-1 | 0 |
| item-2 | sub-1 | uuid-2 | 1 |

---

## Миграции

### 001_create_vpn_sources_and_tags.py

- Создает `vpn_sources`, `vpn_source_tags`, `vpn_source_tag_associations`

### 002_create_subscription_issues.py

- Создает `subscription_issues`, `subscription_issue_items`
- FK связи с CASCADE delete

---

## Важные заметки

### Snapshot тегов

`tags_used` в `subscription_issues` сохраняет snapshot тегов запроса, даже если теги позже изменятся или удалятся. Это позволяет:
- Аудит: какие теги использовались при создании
- Расследование: воспроизвести условия выбора VPN

### Snapshot VPN источников

`subscription_issue_items` сохраняет связь с конкретными VPN источниками на момент создания подписки. Это позволяет:
- Воспроизвести конфиг подписки
- Отслеживать какие VPN были выбраны
- Если VPN источник становится `is_active = false`, он не включается при следующем запросе подписки

### TTL проверка

TTL проверяется при каждом GET запросе `/subscriptions/{public_id}`:
- Если expired → HTTP 403
- Status обновляется на `expired` при первом запросе после expiry

### public_id

- UUID4, непредсказуемый
- Не секрет, но не predictable
- Используется в URL подписки