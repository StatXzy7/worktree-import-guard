# Prepare and authorize 0.1.0

Maintainer documentation; normal users only need README. B1 does not authorize a push, merge, tag,
GitHub Release, package upload or remote configuration.

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
   checkout/PR head identities, artifact IDs/digests and file hashes. Old B0 CI is not new B1 CI.
5. Review evidence and scope. Missing required platform runs mean
   `PREPARED_WITH_VERIFICATION_GAPS`, not `GO_FOR_AUTHORIZED_RELEASE`.

Keep final evidence outside the worktree or in CI artifacts. A summary can reference a prior
verified commit. Do not rebuild repeatedly to write the final SHA into itself. Hashes identify
tested files; cross-environment bitwise reproducibility is not promised.

## External checks and authorization before publication

- Authorize B1 push/PR for new CI and resolve the PR #1 dependency; approve merging separately.
- Recheck PyPI project/version availability, GitHub tags and releases. On 2026-09-10 the PyPI JSON
  endpoint returned HTTP 404, GitHub releases were empty and no remote tags were listed. This is
  a snapshot, not a reservation; network failure is not evidence of name availability.
- Configure and verify a private vulnerability reporting channel (SECURITY.md).
- Authorize final source and workflow activation. Copy the template to
  `.github/workflows/release.yml` only in a separately authorized change.
- Configure the `pypi` GitHub Environment with required reviewers, prevent self-review where
  available and restrict deployment to approved main. Verify the repository plan supports the
  actual protections. An environment name alone provides no protection.
- Configure PyPI Trusted Publishing: project `worktree-import-guard`, owner `StatXzy7`, repository
  `worktree-import-guard`, workflow `release.yml`, environment `pypi`. These are pending fields,
  not an existing publisher or reservation. No long-lived upload token is needed.
- Approve the exact tested files and publication. After uploading, download/check published files,
  verify their identities and runtime-only onboarding, confirm README links resolve on approved
  main, then enable the PyPI README quick start.
  GitHub Release/tag creation is a separate authorized action; TestPyPI is optional later.

## Disabled workflow template

[release.yml.example](release.yml.example) is outside Actions discovery. It only accepts manual
runs on main in this repository and the literal 0.1.0 approval input. It builds once, tests those
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
