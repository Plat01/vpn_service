from abc import ABC, abstractmethod


class SubscriptionConfigGenerator(ABC):
    @abstractmethod
    def generate(self, vpn_uris: list[str]) -> str:
        pass


class TextListConfigGenerator(SubscriptionConfigGenerator):
    def generate(self, vpn_uris: list[str]) -> str:
        return "\n".join(vpn_uris)
