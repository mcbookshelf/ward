import tomllib
from dataclasses import dataclass
from pathlib import Path

from ._coverage import CoverageConfig
from ._exceptions import WardError


@dataclass(frozen=True)
class WardConfig:
    """The settings of ward.toml, or the defaults without one."""

    world: Path | None = None
    origin: tuple[int, int] | None = None
    coverage: CoverageConfig = CoverageConfig()

    @classmethod
    def load(cls, directory: Path | None = None) -> WardConfig:
        """Read the directory's ward.toml; ``world`` is relative to that file."""
        file = (directory or Path.cwd()) / "ward.toml"
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            return cls()
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise WardError(f"Invalid {file.name}: {e}") from e

        world = data.get("world")
        if world is not None and not isinstance(world, str):
            raise WardError(f"Invalid {file.name}: world must be the path of a world folder")
        origin = data.get("origin")
        if origin is not None and not _is_column(origin):
            raise WardError(f"Invalid {file.name}: origin must be [x, z], two whole numbers")
        coverage = CoverageConfig.parse(file.name, data.get("coverage", {}))
        return cls(
            None if world is None else file.parent / world,
            None if origin is None else (origin[0], origin[1]),
            coverage,
        )


def _is_column(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(n, int) and not isinstance(n, bool) for n in value)
    )
