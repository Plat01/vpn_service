# Deployment Information

## Production URL

**Тунелируется трафик на**: `https://sub-oval.online`

- API endpoint: `https://sub-oval.online/api/v1`
- Admin endpoint: `https://sub-oval.online/api/v1/admin/subscriptions/encrypted`
- Subscription endpoint: `https://sub-oval.online/api/v1/subscriptions/{public_id}`
- Docs: `https://sub-oval.online/docs`

## Admin Credentials

- Username: `admin`
- Password: `admin`

## Container Status

- App container: `vpn_service-app-1`
- DB container: `vpn_service-db-1`
- DB port: `5433` (mapped from internal 5432)

## Migration Commands

```bash
# Apply migrations
docker compose exec app alembic upgrade head

# Check current revision
docker compose exec app alembic current

# Rollback last migration
docker compose exec app alembic downgrade -1
```

## Example Subscription Request

```bash
curl -X POST https://sub-oval.online/api/v1/admin/subscriptions/encrypted \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d '{
    "tags": ["bypass", "premium"],
    "ttl_hours": 8,
    "max_devices": 1,
    "metadata": {
      "profile_title": "OvalVPN",
      "profile_update_interval": 1,
      "support_url": "https://t.me/OvalVPN_Bot",
      "profile_web_page_url": "https://t.me/OvalVPN_Bot",
      "announce": "OvalVPN description",
      "traffic_info": {
        "upload": 0,
        "download": 0,
        "total": 524288000
      },
      "info_block": {
        "color": "blue",
        "text": "Support text",
        "button_text": "Support",
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
      "ping_on_open": true
    }
  }'
```