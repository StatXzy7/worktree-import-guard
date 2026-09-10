"""Package-prefix and canonical path containment matching."""

from __future__ import annotations

from pathlib import Path


def module_matches(module_name: str, package: str) -> bool:
    """Return whether *module_name* is the package itself or a submodule."""

    return module_name == package or module_name.startswith(f"{package}.")


def path_is_within(candidate: Path, expected_root: Path) -> bool:
    """Use path components, never string prefixes, for containment."""

    try:
        candidate.relative_to(expected_root)
    except ValueError:
        return False
    return True
