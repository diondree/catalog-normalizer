from dataclasses import dataclass, field

@dataclass(frozen=True)
class NormalizerConfig:
    missing_values: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        normalized_missing_values = frozenset(
            value.strip()
            for value in self.missing_values
        )

        object.__setattr__(
            self,
            "missing_values",
            normalized_missing_values,
        )