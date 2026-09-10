class TagNotFoundError(ValueError):
    def __init__(self, missing_slugs: list[str]):
        self.missing_slugs = missing_slugs
        super().__init__(
            f"Tags not found: {', '.join(missing_slugs)}"
        )