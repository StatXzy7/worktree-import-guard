from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from worktree_import_guard.contracts import ContractError, parse_contract, parse_contracts
from worktree_import_guard.matcher import module_matches, path_is_within
from worktree_import_guard.models import ObservedModule, ReasonCode
from worktree_import_guard.origins import canonicalize_path, resolve_observation


def observation(
    *,
    origin: str | None = None,
    file: str | None = None,
    locations: tuple[str, ...] = (),
) -> ObservedModule:
    return ObservedModule("acme", origin, file, locations, "test", "unit")


def test_contract_parsing_and_duplicates(tmp_path: Path) -> None:
    contract = parse_contract("foo.bar=../source/foo/bar", tmp_path / "tests")
    assert contract.package == "foo.bar"
    assert contract.expected_root == canonicalize_path(tmp_path / "source/foo/bar")

    for malformed in ("acme", "=path", "bad-name=path", "class=path", "acme="):
        with pytest.raises(ContractError):
            parse_contract(malformed, tmp_path)
    with pytest.raises(ContractError, match="duplicate"):
        parse_contracts(["acme=one", "acme=two"], tmp_path)


def test_package_prefix_and_path_component_matching(tmp_path: Path) -> None:
    assert module_matches("acme", "acme")
    assert module_matches("acme.core", "acme")
    assert not module_matches("acme_other", "acme")
    assert path_is_within(tmp_path / "acme/core.py", tmp_path / "acme")
    assert not path_is_within(tmp_path / "acme_other/core.py", tmp_path / "acme")


def test_symlink_or_junction_is_canonicalized(tmp_path: Path) -> None:
    target = tmp_path / "real package"
    target.mkdir()
    link = tmp_path / "linked package"
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
    else:
        link.symlink_to(target, target_is_directory=True)
    assert canonicalize_path(link / "module.py") == canonicalize_path(target / "module.py")


def test_origin_resolution_concrete_and_conflict(tmp_path: Path) -> None:
    module_file = tmp_path / "acme/__init__.py"
    resolved = resolve_observation(observation(origin=str(module_file), file=str(module_file)))
    assert resolved.canonical_origin == canonicalize_path(module_file)
    assert resolved.issue is None

    conflict = resolve_observation(
        observation(origin=str(module_file), file=str(tmp_path / "other/__init__.py"))
    )
    assert conflict.canonical_origin is None
    assert conflict.issue is ReasonCode.ORIGIN_METADATA_CONFLICT


def test_origin_resolution_namespace_and_nonfilesystem(tmp_path: Path) -> None:
    single = resolve_observation(observation(locations=(str(tmp_path / "namespace"),)))
    assert single.canonical_origin == canonicalize_path(tmp_path / "namespace")

    ambiguous = resolve_observation(
        observation(locations=(str(tmp_path / "one"), str(tmp_path / "two")))
    )
    assert ambiguous.issue is ReasonCode.UNSUPPORTED_NAMESPACE_LAYOUT

    builtin = resolve_observation(observation(origin="built-in"))
    assert builtin.issue is ReasonCode.NON_FILESYSTEM_ORIGIN
    unresolved = resolve_observation(observation())
    assert unresolved.issue is ReasonCode.ORIGIN_UNRESOLVED
