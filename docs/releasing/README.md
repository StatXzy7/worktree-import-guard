# Publish the 0.1.1 candidate once authorized

Maintainer documentation; normal users only need README. Source PR/merge authorization
does not authorize tags, GitHub Releases, package uploads or remote configuration.
Version 0.1.1 distinguishes this candidate from old 0.1.0 source previews. The public
README remains pinned to the verified preview until a real release is available.

## Remaining external actions (one release operation)

1. Obtain explicit authorization for PyPI upload, release tag/GitHub Release and
   required Trusted Publisher / GitHub environment configuration. None is implied
   by merging the source PR. Confirm index ownership; a 404 is not a name reservation.
2. Configure the publisher for this repository's reviewed manual release workflow,
   protected `pypi` environment, and the exact approved main commit. Move the existing
   disabled template only within that authorization. Only the publish job gets OIDC.
3. Dispatch version 0.1.1 from that exact main; retain the same built/tested wheel
   and sdist, hashes and CI artifact identity through upload. Create the authorized
   tag and Release for that source; do not rebuild or rename old candidate artifacts.
4. Download from the real PyPI index into a new directory, compare both file hashes
   with the published manifest, install into a fresh environment, verify metadata,
   --version, help, demo, and positive/wrong-source controls. Only then switch the
   homepage to `python -m pip install worktree-import-guard==0.1.1` and mark
   PUBLISHED_AND_SMOKED. A local wheel check does not establish this state.

The artifact test also upgrades the actual pinned 0.1.0 VCS preview to the candidate
using ordinary pip upgrade. It compares all other installed distribution versions
and RECORD mtimes, retaining supported pytest 8.2.0 in that disposable environment.
This is a measured scenario, not a promise of zero dependency changes everywhere.

## Candidate checks

1. Start at an exact clean commit. Record `git rev-parse HEAD`, `git status --porcelain`,
   `git worktree list --porcelain`, Python and pytest versions.
2. Run CONTRIBUTING checks. Build into a new external directory with
   `python -m build --outdir /absolute/new-candidate/dist`. Keep B0 files unchanged.
   Install the additional maintainer-only check tools with `python -m pip install twine pyyaml`.
   For a local package-index Markdown preview, install `"readme_renderer[md]==44.0"` and render
   the wheel METADATA description with `readme_renderer.markdown.render`. This version has
   Windows binary dependencies; the preview is not a live PyPI upload test.
3. Run `python docs/releasing/check_candidate.py --dist /absolute/new-candidate/dist --output
   /absolute/new-candidate/verification` on one line. It checks metadata, wheel onboarding, sdist
   installation and the Hero Demo, writing logs and a manifest without uploading. Add `--uv`
   when validating the uv recipe.
4. Run the same commit through CI, including Windows and Ubuntu artifact jobs. Record run/attempt,
   checkout/PR head identities, artifact IDs/digests and file hashes. Old CI is not candidate CI.
5. Review evidence and scope. Missing required platform runs mean
   `PREPARED_WITH_VERIFICATION_GAPS`, not `GO_FOR_AUTHORIZED_RELEASE`.

Keep final evidence outside the worktree or in CI artifacts. A summary can reference a prior
verified commit. Do not rebuild repeatedly to write the final SHA into itself. Hashes identify
tested files; cross-environment bitwise reproducibility is not promised.

## Publisher configuration details for the operation above

Proposed Trusted Publisher fields: project `worktree-import-guard`, owner `StatXzy7`,
repository `worktree-import-guard`, workflow `release.yml`, environment `pypi`.
These are pending configuration, not an existing publisher or reservation. Use
required reviewers and approved-main deployment restrictions supported by the
repository plan; an environment name alone is not a protection. Do not add a
long-lived upload token. See [PyPI's official publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

Read-only snapshot on 2026-09-11 (Asia/Shanghai): PyPI JSON returned HTTP 404 and
GitHub tags/releases were empty. Recheck at release time. The current candidate
notes are [0.1.1-notes.md](0.1.1-notes.md); 0.1.0 notes remain historical drafts.

## Disabled workflow template

[release.yml.example](release.yml.example) remains outside Actions discovery as a reference copy.
The repository also contains an **enabled** [.github/workflows/release.yml](../../.github/workflows/release.yml)
that follows the same build-once / test-artifacts / publish-after-approval shape. Enabling the
workflow file does **not** mean PyPI already hosts the package, that Trusted Publisher credentials
exist, or that the protected `pypi` environment is configured. Treat PyPI as unpublished until a
real index download and hash verification succeed.

The template only accepts manual
runs on main in this repository and the literal 0.1.1 approval input. It builds once, tests those
exact files on Ubuntu and Windows, then publishes after both jobs and environment approval.
The publish job downloads artifacts from the same run, verifies trusted build-job hashes and never
rebuilds or accepts a user-provided run ID. PRs and ordinary pushes cannot publish. The input does
not substitute for environment protection.

Only the publish job requests `id-token: write`; other jobs have `contents: read`. No job requests
`contents: write`. CI uses ordinary Actions artifact storage and has no package publishing rights.

Full action SHAs were verified via official repository commit APIs on 2026-09-10:

| Official repository | Commit |
| --- | --- |
| actions/checkout | d23441a48e516b6c34aea4fa41551a30e30af803 |
| actions/setup-python | ece7cb06caefa5fff74198d8649806c4678c61a1 |
| actions/upload-artifact | ea165f8d65b6e75b540449e92b4886f43607fa02 |
| actions/download-artifact | d3f86a106a0bac45b974a628896c90dbdf5c8093 |
| pypa/gh-action-pypi-publish | dc37677b2e1c63e2034f94d8a5b11f265b73ba33 |

Reverify pins and requirements when enabling. Commit existence alone does not prove workflow
security. Local structure checks cannot establish actual Actions execution results.

Optional About: “Catch Python tests that pass against the wrong Git worktree.”
Optional topics: `python`, `pytest`, `git-worktree`, `debugging`. No remote settings were changed.
