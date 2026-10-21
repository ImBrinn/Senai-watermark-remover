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
4. **Publish:** after the PR is merged, run Actions → Release → Run workflow
   with `all`, or with `vX.Y.Z`.
   - **Tags:** the workflow tags any untagged version at the first commit on
     `main` that has it (the merge), so nobody has to push tags. Claude cloud sessions can't push tags
     anyway, because the remote hangs up.
   - **Release:** it builds the `.exe` and publishes the release with notes
     from the changelog, marking the newest version as Latest.
   - **From a computer with git:** a person can also push a `vX.Y.Z` tag
     there, which runs the same workflow.

Claude's GitHub tools can't create releases or upload assets, so check the
result with `list_releases` / `get_release_by_tag`. If Actions can't start
(runs end in `startup_failure` with zero jobs), say so plainly. Build the
`.exe` with `/build-exe` and give it to the owner with the changelog section,
so they can upload it under Releases → Draft a new release → choose the tag.
