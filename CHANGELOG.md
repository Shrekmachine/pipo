# Changelog

All notable changes to this project will be documented in this file.

## v1.4.0 - 2026-05-06

- Refactored the app to a `PipoWindow` class to remove global widget state and improve maintainability.
- Moved pip operations to background threads to keep the UI responsive during install, uninstall, refresh, and update tasks.
- Added explicit update controls:
  - `Update Selected` to upgrade only the selected outdated library.
  - `Update All Outdated` to upgrade every outdated library in one run.
- Added right-click package menu actions:
  - `Update Selected`
  - `Show History`
- Added user feedback when no update exists for a package:
  - Log message: `No update found for <package>.`
  - Info dialog popup to make the status clear.
- Rebuilt the Windows executable (`dist/pipo.exe`) for this release.
