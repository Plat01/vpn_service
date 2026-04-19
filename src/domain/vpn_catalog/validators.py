from abc import ABC, abstractmethod

from src.domain.vpn_catalog.validation_errors import VpnUriValidationResult
from src.domain.vpn_catalog.value_objects import VpnUri


class VpnUriValidator(ABC):
    @abstractmethod
    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        pass

    @abstractmethod
    def get_supported_schemes(self) -> list[str]:
        pass
