from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationError:
    message: str


@dataclass(frozen=True)
class VpnUriValidationResult:
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)

    @classmethod
    def success(cls) -> "VpnUriValidationResult":
        return cls(is_valid=True, errors=[])

    @classmethod
    def failure(cls, errors: list[ValidationError]) -> "VpnUriValidationResult":
        return cls(is_valid=False, errors=errors)
