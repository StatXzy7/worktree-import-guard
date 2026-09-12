"""Shared static interpreter probes for onboarding and Skill preflight."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .compatibility import distribution_compatible


@dataclass(frozen=True)
class ProbeResult:
    label: str
    python: str
    python_resolved: str
    python_version: str
    pytest_version: str | None
    pytest_available: bool
    detector_version: str | None
    detector_compatible: bool
    detector_installed: bool
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "python": self.python,
            "python_resolved": self.python_resolved,
            "python_version": self.python_version,
            "pytest_version": self.pytest_version,
            "pytest_available": self.pytest_available,
            "detector_version": self.detector_version,
            "detector_compatible": self.detector_compatible,
            "detector_installed": self.detector_installed,
            "error": self.error,
        }


def python_command(python: Path, *arguments: str) -> str:
    quoted = [shlex.quote(str(python))]
    quoted.extend(shlex.quote(str(argument)) for argument in arguments)
    return " ".join(quoted)


def bounded_cli_command(python: str, *args: str) -> str:
    return python_command(Path(python), "-m", "worktree_import_guard.cli", *args)


def _safe_version() -> str:
    return "{}.{}.{}".format(*sys.version_info[:3])


def _probe_local() -> ProbeResult:
    from importlib.metadata import PackageNotFoundError, distribution
    from importlib.metadata import version as metadata_version

    try:
        pytest_version = metadata_version("pytest")
        parts = tuple(int(value) for value in pytest_version.split(".")[:2])
        pytest_available = (8, 2) <= parts < (10, 0)
    except (PackageNotFoundError, ValueError):
        pytest_version = None
        pytest_available = False

    detector_version: str | None = None
    detector_installed = False
    detector_compatible = False
    try:
        dist = distribution("worktree-import-guard")
    except PackageNotFoundError:
        dist = None
    if dist is not None:
        detector_version = dist.version
        detector_installed = True
        detector_compatible = distribution_compatible(dist)

    return ProbeResult(
        label="current interpreter",
        python=str(Path(sys.executable)),
        python_resolved=str(Path(sys.executable).resolve()),
        python_version=_safe_version(),
        pytest_version=pytest_version,
        pytest_available=pytest_available,
        detector_version=detector_version,
        detector_compatible=detector_compatible,
        detector_installed=detector_installed,
    )


def _probe_subprocess(python: Path, *, label: str) -> ProbeResult:
    script = (
        "import json\n"
        "import sys\n"
        "from importlib.metadata import (\n"
        "    PackageNotFoundError,\n"
        "    distribution,\n"
        "    version as metadata_version,\n"
        ")\n"
        "\n"
        "result = {\n"
        "    'python': sys.executable,\n"
        "    'python_version': sys.version.split()[0],\n"
        "    'pytest_version': None,\n"
        "    'pytest_available': False,\n"
        "    'detector_version': None,\n"
        "    'detector_installed': False,\n"
        "    'detector_compatible': False,\n"
        "}\n"
        "try:\n"
        "    pytest_version = metadata_version('pytest')\n"
        "    parts = tuple(int(value) for value in pytest_version.split('.')[:2])\n"
        "    result['pytest_version'] = pytest_version\n"
        "    result['pytest_available'] = (8, 2) <= parts < (10, 0)\n"
        "except (PackageNotFoundError, ValueError):\n"
        "    pass\n"
        "try:\n"
        "    dist = distribution('worktree-import-guard')\n"
        "    result['detector_version'] = dist.version\n"
        "    result['detector_installed'] = True\n"
        "    from worktree_import_guard.compatibility import distribution_compatible\n"
        "    result['detector_compatible'] = bool(distribution_compatible(dist))\n"
        "except PackageNotFoundError:\n"
        "    pass\n"
        "print(json.dumps(result))\n"
    )
    try:
        completed = subprocess.run(
            [str(python), "-c", script],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as error:
        return ProbeResult(
            label=label,
            python=str(python),
            python_resolved=str(python),
            python_version=_safe_version(),
            pytest_version=None,
            pytest_available=False,
            detector_version=None,
            detector_compatible=False,
            detector_installed=False,
            error=str(error),
        )
    if completed.returncode != 0:
        return ProbeResult(
            label=label,
            python=str(python),
            python_resolved=str(python),
            python_version=_safe_version(),
            pytest_version=None,
            pytest_available=False,
            detector_version=None,
            detector_compatible=False,
            detector_installed=False,
            error=(completed.stderr.strip() or "probe script failed"),
        )
    try:
        data = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as error:
        return ProbeResult(
            label=label,
            python=str(python),
            python_resolved=str(python),
            python_version=_safe_version(),
            pytest_version=None,
            pytest_available=False,
            detector_version=None,
            detector_compatible=False,
            detector_installed=False,
            error=f"malformed probe output: {error}",
        )
    if not isinstance(data, dict):
        return ProbeResult(
            label=label,
            python=str(python),
            python_resolved=str(python),
            python_version=_safe_version(),
            pytest_version=None,
            pytest_available=False,
            detector_version=None,
            detector_compatible=False,
            detector_installed=False,
            error="unexpected probe shape",
        )

    return ProbeResult(
        label=label,
        python=str(data.get("python", str(python))),
        python_resolved=str(python.resolve()),
        python_version=str(data.get("python_version", _safe_version())),
        pytest_version=data.get("pytest_version"),
        pytest_available=bool(data.get("pytest_available")),
        detector_version=data.get("detector_version"),
        detector_compatible=bool(data.get("detector_compatible")),
        detector_installed=bool(data.get("detector_installed")),
    )


def candidate_paths(directory: Path) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = [("current interpreter", Path(sys.executable))]
    if not directory.is_absolute():
        directory = directory.resolve()

    for label in (".venv", "venv"):
        binary = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        items.append((f"{label} environment", directory / label / binary))

    settings = directory / ".vscode" / "settings.json"
    if settings.is_file():
        try:
            payload = json.loads(settings.read_text(encoding="utf-8"))
            python_path = payload.get("python.defaultInterpreterPath")
            if isinstance(python_path, str) and python_path.strip():
                candidate = Path(python_path)
                if not candidate.is_absolute():
                    candidate = (directory / candidate).resolve()
                items.append(("vscode settings", candidate))
        except (json.JSONDecodeError, OSError):
            pass

    py_version = directory / ".python-version"
    if py_version.is_file():
        value = py_version.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if value:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = (directory / candidate).resolve()
            items.append((".python-version", candidate))

    unique: list[tuple[str, Path]] = []
    seen = set[str]()
    for label, path in items:
        if not path.is_file():
            continue
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append((label, path))
    return unique


def probe_candidates(cwd: Path) -> list[dict[str, object]]:
    candidates = []
    for label, python in candidate_paths(cwd):
        if Path(sys.executable) == python:
            raw = _probe_local()
            probe = ProbeResult(
                label=label,
                python=raw.python,
                python_resolved=raw.python_resolved,
                python_version=raw.python_version,
                pytest_version=raw.pytest_version,
                pytest_available=raw.pytest_available,
                detector_version=raw.detector_version,
                detector_compatible=raw.detector_compatible,
                detector_installed=raw.detector_installed,
                error=raw.error,
            )
        else:
            probe = _probe_subprocess(python, label=label)
        payload = probe.as_dict()
        payload["score"] = (
            3 if label == "current interpreter" else 2 if "environment" in label else 1
        )
        payload["command_setup"] = bounded_cli_command(probe.python, "--setup")
        payload["command_doctor"] = bounded_cli_command(probe.python, "--doctor")
        payload["command_check"] = bounded_cli_command(probe.python, "--", "-q")
        candidates.append(payload)
    return candidates


def choose_default_candidate(
    candidates: list[dict[str, object]],
) -> tuple[dict[str, object] | None, bool]:
    ready = [
        item
        for item in candidates
        if not item.get("error") and item.get("pytest_available") and item.get("detector_installed")
    ]
    if not ready:
        return None, False
    best = sorted(
        ready,
        key=lambda item: (
            item.get("score", 0),
            item.get("detector_compatible", False),
            item.get("python_resolved") is not None,
        ),
        reverse=True,
    )
    top = best[0]
    top_score = top.get("score", 0)
    ambiguous = any(
        item is not top
        and item.get("score", 0) == top_score
        and item.get("detector_installed")
        and item.get("pytest_available")
        for item in best[1:]
    )
    return top, ambiguous
