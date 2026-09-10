# Plan: Поддержка HAPP-метаданных в подписках

## Цель

Добавить полную поддержку HAPP-метаданных при создании зашифрованных подписок, включая:
- Профильные заголовки (`profile-title`, `profile-update-interval`, etc.)
- Информацию о трафике (`subscription-userinfo`)
- Информационные блоки (`sub-info`)
- Уведомления об окончании (`sub-expire`)
- Настройки поведения (`behavior`)
- Provider ID для расширенных функций

## Архитектурные принципы

- **DDD**: Metadata как Value Object в domain слое
- **SOLID**: Генератор HAPP-заголовков как отдельный класс в infrastructure
- **Безопасность**: Metadata не логируется в полном виде
- **Расширяемость**: JSONB хранение позволяет добавлять новые поля без миграций

---

## Структура запроса (принятая)

```json
{
  "tags": ["bypass", "premium"],
  "ttl_hours": 72,
  "max_devices": 3,
  
  "metadata": {
    "profile_title": "Немой VPN",
    "profile_update_interval": 1,
    "support_url": "https://t.me/nemoi_support_bot",
    "profile_web_page_url": "https://t.me/nemoi_vpn_bot",
    "announce": "Проверяйте пинг перед подключением",
    
    "traffic_info": {
      "upload": 0,
      "download": 0,
      "total": 0
    },
    
    "info_block": {
      "color": "blue",
      "text": "Для продления подписки обратитесь в поддержку",
      "button_text": "Поддержка",
      "button_link": "https://t.me/nemoi_support_bot"
    },
    
    "expire_notification": {
      "enabled": true,
      "button_link": "https://t.me/nemoi_vpn_bot"
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

---

## Шаги реализации

### 1. Domain Layer - Value Objects

**Файл**: `src/domain/subscription_issuance/value_objects.py`

Добавить новые value objects:

```python
@dataclass(frozen=True)
class TrafficInfo:
    upload: int = 0
    download: int = 0
    total: int = 0
    
    def __post_init__(self):
        if self.upload < 0 or self.download < 0 or self.total < 0:
            raise ValueError("Traffic values must be non-negative")

@dataclass(frozen=True)
class InfoBlock:
    color: str  # "red", "blue", "green"
    text: str
    button_text: str
    button_link: str
    
    def __post_init__(self):
        if self.color not in ("red", "blue", "green"):
            raise ValueError("color must be red, blue, or green")
        if len(self.text) > 200:
            raise ValueError("text must be max 200 characters")
        if len(self.button_text) > 25:
            raise ValueError("button_text must be max 25 characters")

@dataclass(frozen=True)
class ExpireNotification:
    enabled: bool
    button_link: str | None = None

@dataclass(frozen=True)
class SubscriptionBehavior:
    autoconnect: bool = False
    autoconnect_type: str = "lastused"  # "lastused" or "lowestdelay"
    ping_on_open: bool = False
    fallback_url: str | None = None
    
    def __post_init__(self):
        if self.autoconnect_type not in ("lastused", "lowestdelay"):
            raise ValueError("autoconnect_type must be lastused or lowestdelay")

@dataclass(frozen=True)
class SubscriptionMetadata:
    profile_title: str | None = None
    profile_update_interval: int | None = None
    support_url: str | None = None
    profile_web_page_url: str | None = None
    announce: str | None = None
    traffic_info: TrafficInfo | None = None
    info_block: InfoBlock | None = None
    expire_notification: ExpireNotification | None = None
    
    def __post_init__(self):
        if self.profile_title and len(self.profile_title) > 25:
            raise ValueError("profile_title must be max 25 characters")
        if self.profile_update_interval and self.profile_update_interval < 1:
            raise ValueError("profile_update_interval must be at least 1")
        if self.announce and len(self.announce) > 200:
            raise ValueError("announce must be max 200 characters")
```

---

### 2. Domain Layer - Entity Update

**Файл**: `src/domain/subscription_issuance/entities.py`

Добавить поле `metadata` в `SubscriptionIssue`:

```python
@dataclass
class SubscriptionIssue:
    id: SubscriptionIssueId
    public_id: str
    status: SubscriptionStatus
    expires_at: datetime
    max_devices: int | None
    created_at: datetime
    created_by: str
    tags_used: list[str]
    metadata: SubscriptionMetadata | None = None  # NEW
    encrypted_link: str | None = None
    revoked_at: datetime | None = None
```

---

### 3. Infrastructure Layer - Database Migration

**Файл**: `alembic/versions/003_add_subscription_metadata.py`

Добавить JSONB колонки в `subscription_issues`:

```python
def upgrade() -> None:
    op.add_column(
        "subscription_issues",
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "subscription_issues",
        sa.Column("behavior", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "subscription_issues",
        sa.Column("provider_id", sa.String(255), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("subscription_issues", "provider_id")
    op.drop_column("subscription_issues", "behavior")
    op.drop_column("subscription_issues", "metadata")
```

---

### 4. Infrastructure Layer - ORM Model Update

**Файл**: `src/infrastructure/db/models/subscription_issue.py`

```python
class SubscriptionIssueModel(Base):
    __tablename__ = "subscription_issues"
    
    # ... existing fields ...
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    behavior: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

---

### 5. Infrastructure Layer - HAPP Metadata Generator

**Файл**: `src/infrastructure/subscription/happ_metadata_generator.py`

Новый класс для генерации HAPP-заголовков:

```python
import base64
from datetime import datetime

class HappMetadataGenerator:
    def generate_headers(
        self,
        metadata: SubscriptionMetadata | None,
        behavior: SubscriptionBehavior | None,
        provider_id: str | None,
        expires_at: datetime,
        public_id: str,
    ) -> list[str]:
        """Генерирует HAPP-заголовки в формате #field: value"""
        headers = []
        
        if metadata:
            # Profile title
            if metadata.profile_title:
                headers.append(f"#profile-title: {metadata.profile_title}")
            
            # Profile update interval
            if metadata.profile_update_interval:
                headers.append(f"#profile-update-interval: {metadata.profile_update_interval}")
            
            # Subscription userinfo (автоматический expire из expires_at)
            traffic = metadata.traffic_info or TrafficInfo()
            expire_ts = int(expires_at.timestamp())
            userinfo = f"upload={traffic.upload}; download={traffic.download}; total={traffic.total}; expire={expire_ts}"
            headers.append(f"#subscription-userinfo: {userinfo}")
            
            # Support URL
            if metadata.support_url:
                headers.append(f"#support-url: {metadata.support_url}")
            
            # Profile web page URL
            if metadata.profile_web_page_url:
                headers.append(f"#profile-web-page-url: {metadata.profile_web_page_url}")
            
            # Announce (plain text or base64)
            if metadata.announce:
                # Если есть русские символы - base64 encode
                if any(ord(c) > 127 for c in metadata.announce):
                    encoded = base64.b64encode(metadata.announce.encode('utf-8')).decode('ascii')
                    headers.append(f"#announce: base64:{encoded}")
                else:
                    headers.append(f"#announce: {metadata.announce}")
            
            # Info block
            if metadata.info_block:
                headers.append(f"#sub-info-color: {metadata.info_block.color}")
                headers.append(f"#sub-info-text: {metadata.info_block.text}")
                headers.append(f"#sub-info-button-text: {metadata.info_block.button_text}")
                headers.append(f"#sub-info-button-link: {metadata.info_block.button_link}")
            
            # Expire notification
            if metadata.expire_notification and metadata.expire_notification.enabled:
                headers.append(f"#sub-expire: 1")
                if metadata.expire_notification.button_link:
                    headers.append(f"#sub-expire-button-link: {metadata.expire_notification.button_link}")
        
        # Behavior settings
        if behavior:
            if behavior.autoconnect:
                headers.append(f"#subscription-autoconnect: true")
                headers.append(f"#subscription-autoconnect-type: {behavior.autoconnect_type}")
            
            if behavior.ping_on_open:
                headers.append(f"#subscription-ping-onopen-enabled: true")
            
            if behavior.fallback_url:
                # Replace {public_id} placeholder
                url = behavior.fallback_url.replace("{public_id}", public_id)
                headers.append(f"#fallback-url: {url}")
        
        # Provider ID
        if provider_id:
            headers.append(f"#providerid {provider_id}")
        
        return headers
```

---

### 6. Infrastructure Layer - Config Generator Update

**Файл**: `src/infrastructure/subscription/url_generator.py`

Обновить `TextListConfigGenerator`:

```python
class TextListConfigGenerator(SubscriptionConfigGenerator):
    def __init__(self, metadata_generator: HappMetadataGenerator):
        self._metadata_generator = metadata_generator
    
    def generate(
        self,
        vpn_uris: list[str],
        metadata: SubscriptionMetadata | None = None,
        behavior: SubscriptionBehavior | None = None,
        provider_id: str | None = None,
        expires_at: datetime | None = None,
        public_id: str | None = None,
    ) -> str:
        """Генерирует полную подписку с HAPP заголовками"""
        lines = []
        
        # Generate HAPP headers
        if expires_at and public_id:
            headers = self._metadata_generator.generate_headers(
                metadata=metadata,
                behavior=behavior,
                provider_id=provider_id,
                expires_at=expires_at,
                public_id=public_id,
            )
            lines.extend(headers)
        
        # Add separator
        if lines:
            lines.append("")  # Empty line before servers
        
        # Add VPN URIs
        lines.extend(vpn_uris)
        
        return "\n".join(lines)
```

---

### 7. Presentation Layer - HTTP DTO Update

**Файл**: `src/presentation/http/dto/subscription_issuance.py`

```python
class TrafficInfoRequest(BaseModel):
    upload: int = Field(0, ge=0)
    download: int = Field(0, ge=0)
    total: int = Field(0, ge=0)

class InfoBlockRequest(BaseModel):
    color: str = Field(..., pattern="^(red|blue|green)$")
    text: str = Field(..., max_length=200)
    button_text: str = Field(..., max_length=25)
    button_link: str

class ExpireNotificationRequest(BaseModel):
    enabled: bool = True
    button_link: str | None = None

class SubscriptionMetadataRequest(BaseModel):
    profile_title: str | None = Field(None, max_length=25)
    profile_update_interval: int | None = Field(None, ge=1)
    support_url: str | None = None
    profile_web_page_url: str | None = None
    announce: str | None = Field(None, max_length=200)
    traffic_info: TrafficInfoRequest | None = None
    info_block: InfoBlockRequest | None = None
    expire_notification: ExpireNotificationRequest | None = None

class SubscriptionBehaviorRequest(BaseModel):
    autoconnect: bool = False
    autoconnect_type: str = Field("lastused", pattern="^(lastused|lowestdelay)$")
    ping_on_open: bool = False
    fallback_url: str | None = None

class CreateEncryptedSubscriptionRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1)
    ttl_hours: int = Field(..., ge=1, le=8760)
    max_devices: int | None = Field(None, ge=1)
    metadata: SubscriptionMetadataRequest | None = None
    behavior: SubscriptionBehaviorRequest | None = None
    provider_id: str | None = None
```

---

### 8. Application Layer - DTO Update

**Файл**: `src/application/subscription_issuance/dto.py`

```python
@dataclass
class CreateEncryptedSubscriptionDTO:
    tags: list[str]
    ttl_hours: int
    created_by: str
    max_devices: int | None = None
    metadata: SubscriptionMetadata | None = None  # domain value object
    behavior: SubscriptionBehavior | None = None  # domain value object
    provider_id: str | None = None
```

---

### 9. Application Layer - Use Case Update

**Файл**: `src/application/subscription_issuance/use_cases.py`

Обновить `CreateEncryptedSubscriptionUseCase.execute()`:

```python
async def execute(self, dto: CreateEncryptedSubscriptionDTO) -> SubscriptionIssueResultDTO:
    # ... existing VPN source logic ...
    
    subscription_issue = SubscriptionIssue(
        id=SubscriptionIssueId(value=uuid4()),
        public_id=public_id,
        status=SubscriptionStatus.active,
        expires_at=expires_at,
        max_devices=dto.max_devices,
        created_at=now,
        created_by=dto.created_by,
        tags_used=dto.tags,
        metadata=dto.metadata,  # NEW
    )
    
    # ... existing creation logic ...
    
    # Generate config with metadata
    config_content = self._config_generator.generate(
        vpn_uris=vpn_uris,
        metadata=dto.metadata,
        behavior=dto.behavior,
        provider_id=dto.provider_id,
        expires_at=expires_at,
        public_id=public_id,
    )
    
    # ... rest of logic ...
```

Обновить `GetSubscriptionConfigUseCase.execute()`:

```python
async def execute(self, public_id: str) -> tuple[bool, str]:
    # ... existing validation logic ...
    
    # Get VPN URIs
    vpn_uris = [...]
    
    # Generate config with stored metadata
    config_content = self._config_generator.generate(
        vpn_uris=vpn_uris,
        metadata=subscription.metadata,
        behavior=subscription.behavior,
        provider_id=subscription.provider_id,
        expires_at=subscription.expires_at,
        public_id=public_id,
    )
    
    return True, config_content
```

---

### 10. Presentation Layer - Router Update

**Файл**: `src/presentation/http/subscription_issuance_router.py`

Обновить dependency для `HappMetadataGenerator`:

```python
def get_metadata_generator() -> HappMetadataGenerator:
    return HappMetadataGenerator()

def get_config_generator(
    metadata_generator: HappMetadataGenerator = Depends(get_metadata_generator),
) -> TextListConfigGenerator:
    return TextListConfigGenerator(metadata_generator)
```

Обновить handler:

```python
@router.post("/subscriptions/encrypted", ...)
async def create_encrypted_subscription(
    request: CreateEncryptedSubscriptionRequest,
    ...
    config_generator: TextListConfigGenerator = Depends(get_config_generator),
    ...
):
    # Convert request metadata to domain value objects
    metadata = None
    if request.metadata:
        traffic_info = None
        if request.metadata.traffic_info:
            traffic_info = TrafficInfo(
                upload=request.metadata.traffic_info.upload,
                download=request.metadata.traffic_info.download,
                total=request.metadata.traffic_info.total,
            )
        
        info_block = None
        if request.metadata.info_block:
            info_block = InfoBlock(
                color=request.metadata.info_block.color,
                text=request.metadata.info_block.text,
                button_text=request.metadata.info_block.button_text,
                button_link=request.metadata.info_block.button_link,
            )
        
        expire_notification = None
        if request.metadata.expire_notification:
            expire_notification = ExpireNotification(
                enabled=request.metadata.expire_notification.enabled,
                button_link=request.metadata.expire_notification.button_link,
            )
        
        metadata = SubscriptionMetadata(
            profile_title=request.metadata.profile_title,
            profile_update_interval=request.metadata.profile_update_interval,
            support_url=request.metadata.support_url,
            profile_web_page_url=request.metadata.profile_web_page_url,
            announce=request.metadata.announce,
            traffic_info=traffic_info,
            info_block=info_block,
            expire_notification=expire_notification,
        )
    
    behavior = None
    if request.behavior:
        behavior = SubscriptionBehavior(
            autoconnect=request.behavior.autoconnect,
            autoconnect_type=request.behavior.autoconnect_type,
            ping_on_open=request.behavior.ping_on_open,
            fallback_url=request.behavior.fallback_url,
        )
    
    dto = CreateEncryptedSubscriptionDTO(
        tags=request.tags,
        ttl_hours=request.ttl_hours,
        created_by=admin,
        max_devices=request.max_devices,
        metadata=metadata,
        behavior=behavior,
        provider_id=request.provider_id,
    )
    
    # ... rest of handler ...
```

---

### 11. Repository Update

**Файл**: `src/infrastructure/db/repositories/subscription_issue.py`

Обновить маппинг ORM <-> Domain:

```python
def _to_domain(self, model: SubscriptionIssueModel) -> SubscriptionIssue:
    metadata = None
    if model.metadata:
        metadata = self._map_metadata_from_db(model.metadata)
    
    behavior = None
    if model.behavior:
        behavior = self._map_behavior_from_db(model.behavior)
    
    return SubscriptionIssue(
        id=SubscriptionIssueId(value=model.id),
        public_id=model.public_id,
        status=SubscriptionStatus(model.status),
        expires_at=model.expires_at,
        max_devices=model.max_devices,
        created_at=model.created_at,
        created_by=model.created_by,
        tags_used=model.tags_used,
        metadata=metadata,
        behavior=behavior,
        provider_id=model.provider_id,
        encrypted_link=model.encrypted_link,
        revoked_at=model.revoked_at,
    )

def _map_metadata_from_db(self, data: dict) -> SubscriptionMetadata:
    # Convert JSON dict to domain value objects
    traffic_info = None
    if "traffic_info" in data:
        traffic_info = TrafficInfo(**data["traffic_info"])
    
    info_block = None
    if "info_block" in data:
        info_block = InfoBlock(**data["info_block"])
    
    expire_notification = None
    if "expire_notification" in data:
        expire_notification = ExpireNotification(**data["expire_notification"])
    
    return SubscriptionMetadata(
        profile_title=data.get("profile_title"),
        profile_update_interval=data.get("profile_update_interval"),
        support_url=data.get("support_url"),
        profile_web_page_url=data.get("profile_web_page_url"),
        announce=data.get("announce"),
        traffic_info=traffic_info,
        info_block=info_block,
        expire_notification=expire_notification,
    )

def _to_model(self, entity: SubscriptionIssue) -> SubscriptionIssueModel:
    metadata_dict = None
    if entity.metadata:
        metadata_dict = self._map_metadata_to_db(entity.metadata)
    
    behavior_dict = None
    if entity.behavior:
        behavior_dict = self._map_behavior_to_db(entity.behavior)
    
    return SubscriptionIssueModel(
        id=entity.id.value,
        public_id=entity.public_id,
        status=entity.status.value,
        expires_at=entity.expires_at,
        max_devices=entity.max_devices,
        created_at=entity.created_at,
        created_by=entity.created_by,
        tags_used=entity.tags_used,
        metadata=metadata_dict,
        behavior=behavior_dict,
        provider_id=entity.provider_id,
        encrypted_link=entity.encrypted_link,
        revoked_at=entity.revoked_at,
    )

def _map_metadata_to_db(self, metadata: SubscriptionMetadata) -> dict:
    data = {}
    if metadata.profile_title:
        data["profile_title"] = metadata.profile_title
    if metadata.profile_update_interval:
        data["profile_update_interval"] = metadata.profile_update_interval
    if metadata.support_url:
        data["support_url"] = metadata.support_url
    if metadata.profile_web_page_url:
        data["profile_web_page_url"] = metadata.profile_web_page_url
    if metadata.announce:
        data["announce"] = metadata.announce
    if metadata.traffic_info:
        data["traffic_info"] = {
            "upload": metadata.traffic_info.upload,
            "download": metadata.traffic_info.download,
            "total": metadata.traffic_info.total,
        }
    if metadata.info_block:
        data["info_block"] = {
            "color": metadata.info_block.color,
            "text": metadata.info_block.text,
            "button_text": metadata.info_block.button_text,
            "button_link": metadata.info_block.button_link,
        }
    if metadata.expire_notification:
        data["expire_notification"] = {
            "enabled": metadata.expire_notification.enabled,
            "button_link": metadata.expire_notification.button_link,
        }
    return data
```

---

### 12. Tests

**Файл**: `tests/test_happ_metadata_generator.py`

```python
import pytest
from datetime import datetime, timezone

from src.infrastructure.subscription.happ_metadata_generator import HappMetadataGenerator
from src.domain.subscription_issuance.value_objects import (
    TrafficInfo,
    InfoBlock,
    ExpireNotification,
    SubscriptionMetadata,
    SubscriptionBehavior,
)

class TestHappMetadataGenerator:
    def test_generate_headers_with_full_metadata(self):
        generator = HappMetadataGenerator()
        
        traffic = TrafficInfo(upload=0, download=2153701362, total=10737418240)
        info_block = InfoBlock(
            color="blue",
            text="Для продления обратитесь в поддержку",
            button_text="Поддержка",
            button_link="https://t.me/bot",
        )
        expire_notification = ExpireNotification(enabled=True, button_link="https://t.me/bot")
        
        metadata = SubscriptionMetadata(
            profile_title="Немой VPN",
            profile_update_interval=1,
            support_url="https://t.me/support",
            profile_web_page_url="https://t.me/main",
            announce="Проверяйте пинг",
            traffic_info=traffic,
            info_block=info_block,
            expire_notification=expire_notification,
        )
        
        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        
        headers = generator.generate_headers(
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test-123",
        )
        
        assert "#profile-title: Немой VPN" in headers
        assert "#profile-update-interval: 1" in headers
        assert "#subscription-userinfo: upload=0; download=2153701362; total=10737418240; expire=" in headers[2]
        assert "#support-url: https://t.me/support" in headers
        assert "#announce: Проверяйте пинг" in headers
        assert "#sub-info-color: blue" in headers
        assert "#sub-expire: 1" in headers
    
    def test_generate_headers_with_russian_announce_base64(self):
        generator = HappMetadataGenerator()
        
        metadata = SubscriptionMetadata(
            announce="Проверяйте пинг перед подключением",
        )
        
        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        
        headers = generator.generate_headers(
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test",
        )
        
        # Should be base64 encoded because contains Russian characters
        assert "#announce: base64:" in headers[0]
    
    def test_generate_headers_with_behavior(self):
        generator = HappMetadataGenerator()
        
        behavior = SubscriptionBehavior(
            autoconnect=True,
            autoconnect_type="lowestdelay",
            ping_on_open=True,
            fallback_url="https://backup.example.com/{public_id}",
        )
        
        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        
        headers = generator.generate_headers(
            metadata=None,
            behavior=behavior,
            provider_id=None,
            expires_at=expires_at,
            public_id="abc-123",
        )
        
        assert "#subscription-autoconnect: true" in headers
        assert "#subscription-autoconnect-type: lowestdelay" in headers
        assert "#subscription-ping-onopen-enabled: true" in headers
        assert "#fallback-url: https://backup.example.com/abc-123" in headers
    
    def test_generate_headers_with_provider_id(self):
        generator = HappMetadataGenerator()
        
        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        
        headers = generator.generate_headers(
            metadata=None,
            behavior=None,
            provider_id="PROVIDER_123",
            expires_at=expires_at,
            public_id="test",
        )
        
        assert "#providerid PROVIDER_123" in headers
```

**Файл**: `tests/test_config_generator_with_metadata.py`

```python
import pytest
from datetime import datetime, timezone

from src.infrastructure.subscription.url_generator import TextListConfigGenerator
from src.infrastructure.subscription.happ_metadata_generator import HappMetadataGenerator
from src.domain.subscription_issuance.value_objects import SubscriptionMetadata

class TestTextListConfigGeneratorWithMetadata:
    def test_generate_with_metadata(self):
        metadata_generator = HappMetadataGenerator()
        config_generator = TextListConfigGenerator(metadata_generator)
        
        metadata = SubscriptionMetadata(
            profile_title="Test VPN",
            profile_update_interval=1,
        )
        
        vpn_uris = [
            "vless://uuid@server1:443?security=reality#Server1",
            "vless://uuid@server2:443?security=reality#Server2",
        ]
        
        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        
        config = config_generator.generate(
            vpn_uris=vpn_uris,
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test-id",
        )
        
        assert "#profile-title: Test VPN" in config
        assert "#profile-update-interval: 1" in config
        assert "#subscription-userinfo:" in config
        assert "vless://uuid@server1:443" in config
        assert "vless://uuid@server2:443" in config
    
    def test_generate_without_metadata(self):
        metadata_generator = HappMetadataGenerator()
        config_generator = TextListConfigGenerator(metadata_generator)
        
        vpn_uris = ["vless://uuid@server:443"]
        
        config = config_generator.generate(vpn_uris=vpn_uris)
        
        assert config == "vless://uuid@server:443"
```

---

## Структура файлов (итоговая)

```
src/
  domain/
    subscription_issuance/
      value_objects.py          # + TrafficInfo, InfoBlock, ExpireNotification, SubscriptionBehavior, SubscriptionMetadata
      entities.py               # + metadata field
  
  application/
    subscription_issuance/
      dto.py                    # + metadata, behavior, provider_id
      use_cases.py              # + metadata handling
  
  infrastructure/
    db/
      models/
        subscription_issue.py   # + metadata, behavior, provider_id JSONB columns
      repositories/
        subscription_issue.py   # + metadata mapping
    subscription/
      happ_metadata_generator.py  # NEW - HAPP headers generator
      url_generator.py            # Updated - accepts metadata
  
  presentation/
    http/
      dto/
        subscription_issuance.py  # + nested metadata DTOs
      subscription_issuance_router.py  # + metadata conversion

alembic/
  versions/
    003_add_subscription_metadata.py  # NEW migration

tests/
  test_happ_metadata_generator.py      # NEW
  test_config_generator_with_metadata.py  # NEW
  test_subscription_use_cases.py       # Update existing tests
```

---

## Проверка безопасности

### Что НЕ логируется
- Полные metadata (profile_title, support_url, announce могут быть чувствительными)
- Provider ID
- Fallback URL с public_id

### Что логируется
- Fingerprint: `metadata present: true/false`
- Count: `metadata fields count: 5`
- Hash: `metadata_hash: abc123...`

### Пример безопасного логирования

```python
metadata_fingerprint = "present" if dto.metadata else "none"
logger.info(
    "Subscription created: id=%s, metadata=%s, ttl_hours=%d",
    subscription.id.value,
    metadata_fingerprint,
    dto.ttl_hours,
)
```

---

## Definition of Done

- [ ] Domain value objects созданы
- [ ] Entity обновлена с metadata field
- [ ] Migration создана и протестирована
- [ ] ORM model обновлена
- [ ] HAPP metadata generator создан
- [ ] Config generator обновлен
- [ ] HTTP DTO обновлены
- [ ] Application DTO обновлены
- [ ] Use cases обновлены
- [ ] Router обновлен
- [ ] Repository маппинг обновлен
- [ ] Unit tests написаны
- [ ] Integration tests обновлены
- [ ] Безопасность логирования проверена
- [ ] Документация обновлена (docs/encrypted-subscription-flow.md)

---

## Варианты реализации (объяснение выбора)

### Вариант 1: Metadata как отдельная таблица (НЕ выбран)
- Таблицы: `subscription_metadata`, `subscription_info_blocks`, etc.
- **Плюсы**: Более строгая структура, SQL queries по metadata
- **Минусы**: Overhead для простой структуры, много JOIN, сложнее расширять
- **Почему не выбран**: HAPP metadata — это display information, не бизнес-данные; JSONB достаточно

### Вариант 2: Metadata как JSONB в subscription_issues (Выбран)
- **Плюсы**: Простота, гибкость, одна таблица, легко добавлять новые HAPP fields
- **Минусы**: No SQL queries по metadata fields (но не нужно)
- **Почему выбран**: Metadata не используется для бизнес-логики, только для display; HAPP fields могут меняться; JSONB идеально для semi-structured display data

### Вариант 3: Metadata как fields в entity (НЕ выбран)
- Все поля metadata как отдельные columns
- **Плюсы**: Type safety на уровне БД
- **Минусы**: Migration explosion при каждом новом HAPP field, over-engineering
- **Почему не выбран**: HAPP specification не фиксирована, новые fields могут появляться

---

## Future considerations

1. **OAuth2/OIDC**: Metadata может связываться с user profile (например, personal announce)
2. **Personal cabinet**: User может редактировать свой `profile_title`, `announce`
3. **Analytics**: Можно добавить tracking_id в behavior для статистики
4. **A/B testing**: Different metadata templates для testing UX

---

## Questions to user

Нет вопросов — структура запроса утверждена пользователем.