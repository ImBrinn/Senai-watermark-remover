---
name: release
description: Cut a new version of SenAI Watermark Remover (version bump, CHANGELOG section, tag, GitHub release with the Windows exe). Use when asked to release, publish, tag or version the app.
---

# Release a version

1. **Version:** set `__version__` in `senai_remover/__init__.py` to `X.Y.Z`
   (semver: new features bump the minor version, fixes bump the patch).
2. **Changelog:** add `## [X.Y.Z] - YYYY-MM-DD` at the top of `CHANGELOG.md`,
   with `### Added` / `### Changed` / `### Fixed` bullets in plain language,
   plus a `[X.Y.Z]: https://github.com/ImBrinn/Senai-watermark-remover/releases/tag/vX.Y.Z`
   link at the bottom. The heading must start with exactly `## [X.Y.Z]`,
   because the workflow extracts the notes by that line.
3. **Check:** run the tests and pyflakes, regenerate screenshots if anything
   visual changed (`/screenshots`), and open a PR.
4. **Tag:** after the PR is merged, tag the merge commit and push:
   `git fetch origin main && git tag -a vX.Y.Z origin/main -m "SenAI Watermark Remover vX.Y.Z" && git push origin vX.Y.Z`
5. **Publish:** the tag push runs `.github/workflows/release.yml`, which builds
   the `.exe` for the tag and creates the release, with notes from the
   changelog and marked Latest if it's the newest tag. To rebuild or backfill,
   go to Actions → Release → Run workflow and enter a list of tags, or `all`.

Claude's GitHub tools can't create releases or upload assets, so check the
result with `list_releases` / `get_release_by_tag`. If Actions can't start
(runs end in `startup_failure` with zero jobs), say so plainly. Build the
`.exe` with `/build-exe` and give it to the owner with the changelog section,
so they can upload it under Releases → Draft a new release → choose the tag.
