from dataclasses import dataclass


@dataclass
class ParsedUriDTO:
    line_number: int
    raw_uri: str
    name: str | None
    is_valid: bool
    error: str | None


class PlainTextUriParser:
    MAX_LINES = 500

    def parse(self, text: str) -> list[ParsedUriDTO]:
        lines = text.strip().split("\n")
        if len(lines) > self.MAX_LINES:
            raise ValueError(f"Too many lines: max {self.MAX_LINES}")

        result = []
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            uri_part, fragment = self._extract_fragment(stripped)

            result.append(ParsedUriDTO(
                line_number=i,
                raw_uri=uri_part,
                name=fragment,
                is_valid=True,
                error=None,
            ))

        return result

    def _extract_fragment(self, uri: str) -> tuple[str, str | None]:
        if "#" in uri:
            scheme_part = uri.split("://")[0] if "://" in uri else ""
            rest = uri.split("://", 1)[1] if "://" in uri else uri

            if "#" in rest:
                before_fragment = rest.split("#", 1)[0]
                fragment = rest.split("#", 1)[1] if len(rest.split("#", 1)) > 1 else None
                return f"{scheme_part}://{before_fragment}" if scheme_part else before_fragment, fragment

        return uri, None

    def mask_uri_for_logging(self, uri: str) -> str:
        scheme = uri.split("://")[0] if "://" in uri else ""
        if scheme in ("vless", "vmess"):
            return f"{scheme}://***MASKED***@***MASKED***"
        elif scheme in ("trojan", "ss"):
            return f"{scheme}://***MASKED***@***MASKED***"
        return f"{scheme}://***MASKED***" if scheme else "***MASKED***"