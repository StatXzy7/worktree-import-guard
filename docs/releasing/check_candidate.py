"""Verify existing candidate files without uploading or changing repository settings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from email.parser import BytesParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], cwd: Path, log: Path, *, env=None, expected: int = 0) -> str:
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=child_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log.write_text(json.dumps(command) + "\n" + result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != expected:
        raise RuntimeError(f"Expected exit {expected}, got {result.returncode}; see {log}")
    print(f"PASS {log.name}", flush=True)
    return result.stdout


def identity(path: Path) -> dict:
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def script(venv: Path, name: str) -> str:
    return str(
        venv
        / ("Scripts" if sys.platform == "win32" else "bin")
        / (name + (".exe" if sys.platform == "win32" else ""))
    )


def check_workflows() -> None:
    template = ROOT / "docs/releasing/release.yml.example"
    active_release = ROOT / ".github/workflows/release.yml"
    paths = [ROOT / ".github/workflows/ci.yml", template]
    if active_release.exists():
        paths.append(active_release)
    for path in paths:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        assert data["permissions"] == {"contents": "read"}, path
        for job in data["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    assert re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", step["uses"]), step
                assert "run-id" not in step.get("with", {}), step
        if path in (template, active_release):
            assert set(data["on"]) == {"workflow_dispatch"}
            jobs = data["jobs"]
            assert jobs["publish"]["needs"] == ["build", "test-files"]
            assert jobs["publish"]["permissions"] == {"id-token": "write"}
            assert jobs["publish"]["environment"]["name"] == "pypi"
            for name in ("build", "publish"):
                for restriction in (
                    "refs/heads/main",
                    "workflow_dispatch",
                    "0.1.0",
                    "StatXzy7/worktree-import-guard",
                ):
                    assert restriction in jobs[name]["if"]
            assert set(jobs["test-files"]["strategy"]["matrix"]["os"]) == {
                "ubuntu-latest",
                "windows-latest",
            }
            assert all("permissions" not in job for name, job in jobs.items() if name != "publish")
        else:
            assert "id-token" not in path.read_text(encoding="utf-8")


def check_uv(wheel: Path, output: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("--uv requires uv on PATH")
    project = output / "uv project"
    project.mkdir()
    config = project / "pyproject.toml"
    config.write_text(
        '[project]\nname="uv-smoke"\nversion="0.0.0"\ndependencies=[]\n', encoding="utf-8"
    )
    env = os.environ.copy()
    for key in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH", "PYTEST_ADDOPTS"):
        env.pop(key, None)
    run([uv, "--version"], project, output / "uv-version.log")
    run([uv, "sync", "--python", sys.executable], project, output / "uv-setup.log", env=env)
    python = script(project / ".venv", "python")
    run(
        [uv, "pip", "install", "--python", python, str(wheel)],
        project,
        output / "uv-manual-install.log",
        env=env,
    )
    run(
        [uv, "run", "--no-sync", "wt-import", "--version"],
        project,
        output / "uv-no-sync.log",
        env=env,
    )
    run(
        [uv, "pip", "show", "--python", python, "typing-extensions"],
        project,
        output / "uv-before-sync-missing.log",
        env=env,
        expected=1,
    )
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "dependencies=[]", 'dependencies=["typing-extensions"]'
        ),
        encoding="utf-8",
    )
    run([uv, "run", "wt-import", "--version"], project, output / "uv-run-sync.log", env=env)
    run(
        [uv, "pip", "show", "--python", python, "typing-extensions"],
        project,
        output / "uv-run-installed-dependency.log",
        env=env,
    )
    run([uv, "sync"], project, output / "uv-exact-sync.log", env=env)
    assert not Path(script(project / ".venv", "wt-import")).exists()
    run(
        [uv, "pip", "show", "--python", python, "worktree-import-guard"],
        project,
        output / "uv-extra-removed.log",
        env=env,
        expected=1,
    )
    run([uv, "add", "--dev", str(wheel)], project, output / "uv-declare.log", env=env)
    run([uv, "sync"], project, output / "uv-declared-sync.log", env=env)
    run(
        [uv, "run", "--no-sync", "wt-import", "--version"],
        project,
        output / "uv-declared-retained.log",
        env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--uv", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    dist = args.dist.resolve()
    wheel = dist / "worktree_import_guard-0.1.0-py3-none-any.whl"
    sdist = dist / "worktree_import_guard-0.1.0.tar.gz"
    files = [identity(wheel), identity(sdist)]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    source = run(["git", "rev-parse", "HEAD"], ROOT, output / "source.log").strip()
    status = run(["git", "status", "--porcelain"], ROOT, output / "status.log")
    if status.strip():
        raise RuntimeError("Candidate verification requires a clean source commit")
    checkout = run(["git", "worktree", "list", "--porcelain"], ROOT, output / "checkout.log")
    manifest = {
        "source_commit": source,
        "checkout_path": str(ROOT),
        "worktree_status": status,
        "worktrees": checkout,
        "files": files,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "ci_run_id": os.environ.get("GITHUB_RUN_ID"),
        "ci_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "ci_workflow_sha": os.environ.get("GITHUB_WORKFLOW_SHA"),
        "ci_artifact_id": None,
        "ci_artifact_note": "Attach artifact service ID after upload, if any",
        "result": "incomplete",
        "uv": "requested" if args.uv else "not run",
        "scope": "candidate only; no upload; local checks do not establish other-platform CI",
    }
    manifest_path = output / "manifest.json"
    try:
        check_workflows()
        with zipfile.ZipFile(wheel) as archive:
            metadata = BytesParser().parsebytes(
                archive.read("worktree_import_guard-0.1.0.dist-info/METADATA")
            )
            assert metadata["Name"] == "worktree-import-guard" and metadata["Version"] == "0.1.0"
            assert metadata["Description-Content-Type"] == "text/markdown"
            runtime = [r for r in metadata.get_all("Requires-Dist", []) if "extra ==" not in r]
            assert len(runtime) == 1 and runtime[0].startswith("pytest"), runtime
            manifest["runtime_dependencies"] = runtime
            assert "LICENSE" in " ".join(archive.namelist())
        with tarfile.open(sdist) as archive:
            member = archive.extractfile("worktree_import_guard-0.1.0/PKG-INFO")
            assert member is not None
            assert BytesParser().parsebytes(member.read())["Version"] == "0.1.0"
        run(
            [sys.executable, "-m", "twine", "check", "--strict", str(wheel), str(sdist)],
            ROOT,
            output / "metadata.log",
            env=env,
        )
        env["WTIG_RUN_ARTIFACT_TESTS"] = "1"
        env["WTIG_ARTIFACT_WHEEL"] = str(wheel)
        junit = output / "artifact.xml"
        pytest_script = str(
            Path(sys.executable).parent / ("pytest.exe" if os.name == "nt" else "pytest")
        )
        if not Path(pytest_script).is_file():
            import sysconfig

            pytest_script = str(
                Path(sysconfig.get_path("scripts"))
                / ("pytest.exe" if os.name == "nt" else "pytest")
            )
        manifest["pytest"] = run(
            [pytest_script, "--version"], ROOT, output / "pytest-version.log"
        ).strip()
        run(
            [pytest_script, "tests/artifact", "-q", "-rA", f"--junitxml={junit}"],
            ROOT,
            output / "onboarding.log",
            env=env,
        )
        suites = ET.parse(junit).getroot().iter("testsuite")
        counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
        for suite in suites:
            for key in counts:
                counts[key] += int(suite.attrib.get(key, 0))
        assert counts["tests"] >= 3 and not any(
            counts[k] for k in ("failures", "errors", "skipped")
        )
        manifest["artifact_tests"] = counts
        run(
            [
                sys.executable,
                str(ROOT / "examples/cross-worktree-demo/run.py"),
                "--wheel",
                str(wheel),
            ],
            output,
            output / "demo.log",
            env=env,
        )
        derived = output / "sdist-wheel"
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--wheel-dir",
                str(derived),
                str(sdist),
            ],
            output,
            output / "sdist-build.log",
            env=env,
        )
        derived_wheel = next(derived.glob("*.whl"))
        manifest["sdist_derived_wheel"] = identity(derived_wheel)
        venv = output / "sdist venv"
        run([sys.executable, "-m", "venv", str(venv)], output, output / "sdist-venv.log", env=env)
        run(
            [script(venv, "python"), "-m", "pip", "install", str(derived_wheel)],
            output,
            output / "sdist-install.log",
            env=env,
        )
        run([script(venv, "wt-import"), "--help"], output, output / "sdist-help.log", env=env)
        assert (
            run(
                [script(venv, "wt-import"), "--version"],
                output,
                output / "sdist-version.log",
                env=env,
            ).strip()
            == "wt-import 0.1.0"
        )
        if args.uv:
            check_uv(wheel, output)
            manifest["uv"] = "pass"
        assert files == [identity(wheel), identity(sdist)], "Candidate files changed during tests"
        manifest["result"] = "passed on recorded platform"
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
