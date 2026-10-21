---
name: screenshots
description: Regenerate and review the app's screenshots, the Settings theme preview images and the README images after any visual change to a theme or the settings bar. Use when a theme's look changes, when adding a theme, or when asked for screenshots.
---

# Screenshots

```bash
python3 tools/screenshots.py <scratchpad>/shots [theme numbers]   # review set: empty / listed / done × light / dark
python3 tools/screenshots.py --previews   # senai_remover/gui/assets/previews/<id>-<light|dark>.png (Settings cards)
python3 tools/screenshots.py --docs       # docs/screenshots/<id>-<light|dark>.png and settings-<light|dark>.png
```

- **Isolation:** the tool runs offscreen, with reduced motion and a throwaway
  settings file, so your saved theme is never changed.
- **Review:** Read every PNG you produce. Check for clipping, overlapping or
  cut-off text, focus rings, selection, the warning and error rows, and that
  dark really is dark.
- **Size:** after `--docs`, re-save the PNGs with Pillow (`optimize=True`) to
  keep them small. They should be about 50–95 KB each.
- **Commit:** the previews are in the package data, so commit them along with
  the theme change.
