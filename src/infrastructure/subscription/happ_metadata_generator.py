import base64
from datetime import datetime

from src.domain.subscription_issuance.value_objects import (
    SubscriptionBehavior,
    SubscriptionMetadata,
    TrafficInfo,
)


class HappMetadataGenerator:
    def generate_headers(
        self,
        metadata: SubscriptionMetadata | None,
        behavior: SubscriptionBehavior | None,
        provider_id: str | None,
        expires_at: datetime,
        public_id: str,
    ) -> list[str]:
        headers = []

        if metadata:
            if metadata.profile_title:
                headers.append(f"#profile-title: {metadata.profile_title}")

            if metadata.profile_update_interval:
                headers.append(
                    f"#profile-update-interval: {metadata.profile_update_interval}"
                )

            traffic = metadata.traffic_info or TrafficInfo()
            expire_ts = int(expires_at.timestamp())
            userinfo = f"upload={traffic.upload}; download={traffic.download}; total={traffic.total}; expire={expire_ts}"
            headers.append(f"#subscription-userinfo: {userinfo}")

            if metadata.support_url:
                headers.append(f"#support-url: {metadata.support_url}")

            if metadata.profile_web_page_url:
                headers.append(
                    f"#profile-web-page-url: {metadata.profile_web_page_url}"
                )

            if metadata.announce:
                if any(ord(c) > 127 for c in metadata.announce):
                    encoded = base64.b64encode(
                        metadata.announce.encode("utf-8")
                    ).decode("ascii")
                    headers.append(f"#announce: base64:{encoded}")
                else:
                    headers.append(f"#announce: {metadata.announce}")

            if metadata.info_block:
                headers.append(f"#sub-info-color: {metadata.info_block.color}")
                headers.append(f"#sub-info-text: {metadata.info_block.text}")
                headers.append(
                    f"#sub-info-button-text: {metadata.info_block.button_text}"
                )
                headers.append(
                    f"#sub-info-button-link: {metadata.info_block.button_link}"
                )

            if metadata.expire_notification and metadata.expire_notification.enabled:
                headers.append("#sub-expire: 1")
                if metadata.expire_notification.button_link:
                    headers.append(
                        f"#sub-expire-button-link: {metadata.expire_notification.button_link}"
                    )

        if behavior:
            if behavior.autoconnect:
                headers.append("#subscription-autoconnect: true")
                headers.append(
                    f"#subscription-autoconnect-type: {behavior.autoconnect_type}"
                )

            if behavior.ping_on_open:
                headers.append("#subscription-ping-onopen-enabled: true")

            if behavior.fallback_url:
                url = behavior.fallback_url.replace("{public_id}", public_id)
                headers.append(f"#fallback-url: {url}")

        if provider_id:
            headers.append(f"#providerid {provider_id}")

        return headers
