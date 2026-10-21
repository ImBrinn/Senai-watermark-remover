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
   with `all`, or with `vX.Y.Z`. Claude can start it with the GitHub MCP tool
   `actions_run_trigger` (`run_workflow`, workflow `release.yml`, ref `main`,
   inputs `{"tags": "vX.Y.Z"}`), then watch the run until every job finishes.
   - **Tags:** the workflow tags any untagged version at the first commit on
     `main` that has it (the merge), so nobody has to push tags. Claude cloud
     sessions can't push tags anyway (HTTP 403).
   - **Release:** it builds the `.exe` and publishes the release with notes
     from the changelog, marking the newest version as Latest.
   - **From a computer with git:** a person can also push a `vX.Y.Z` tag
     there, which runs the same workflow.

Claude's GitHub tools can't create releases or upload assets, so the workflow
does it. Afterwards, check:
- `list_releases`: the new version is there with `SenAI-Watermark-Remover.exe`
  attached.
- `/releases/latest/download/SenAI-Watermark-Remover.exe` downloads.

If a run fails before any job starts, read the job's annotations
(`https://api.github.com/repos/ImBrinn/Senai-watermark-remover/check-runs/<job id>/annotations`)
and tell the owner the reason plainly; a billing lock is theirs to fix. Then
build the `.exe` with `/build-exe` and give it to them with the changelog
section, so they can upload it under Releases → Draft a new release → choose
the tag.
