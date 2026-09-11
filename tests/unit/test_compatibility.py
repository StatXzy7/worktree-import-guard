"""Shared preview/candidate compatibility checks."""


import pytest

from worktree_import_guard.compatibility import (
    VERIFIED_PREVIEW_COMMIT,
    direct_url_commit,
    distribution_compatible,
)


class FakeDist:
    def __init__(self, version: str, commit: str | None = None) -> None:
        self.version = version
        self._commit = commit

    def read_text(self, name: str) -> str:
        if name != "direct_url.json" or self._commit is None:
            raise OSError("missing")
        return (
            '{"url":"git+https://github.com/StatXzy7/worktree-import-guard.git@'
            + self._commit
            + '","vcs_info":{"commit_id":"'
            + self._commit
            + '"}}'
        )


@pytest.mark.parametrize(
    ("version", "commit", "expected"),
    [
        ("0.1.1", None, True),
        ("0.1.0", VERIFIED_PREVIEW_COMMIT, True),
        ("0.1.0", "deadbeef" * 5, False),
        ("0.1.0", None, False),
        ("0.2.0", None, False),
    ],
)
def test_distribution_compatible(version: str, commit: str | None, expected: bool) -> None:
    assert distribution_compatible(FakeDist(version, commit)) is expected


def test_direct_url_commit_parses_vcs_metadata() -> None:
    dist = FakeDist("0.1.0", VERIFIED_PREVIEW_COMMIT)
    assert direct_url_commit(dist) == VERIFIED_PREVIEW_COMMIT
    assert direct_url_commit(FakeDist("0.1.0", None)) is None
