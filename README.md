# Pipo - Python Pip Manager Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Pipo is a desktop GUI tool for managing Python packages with `pip`.
It gives you a simple visual workflow to install, uninstall, inspect, and update packages without using terminal commands manually.

**Version:** defined as `__version__` in [`pipo.py`](pipo.py) (currently **1.2.0**).

## Features

- View installed Python packages in a list
- Install new packages
- Uninstall selected packages
- Check for outdated packages
- Update all outdated packages in one flow
- Show package metadata (`pip show`)
- Show version history (`pip index versions`)
- **Theme selector:** System (follow OS), Light, or Dark (Fusion style)

## Tech Stack

- Python 3
- [PySide6](https://wiki.qt.io/Qt_for_Python) (Qt for Python, widgets GUI)
- `pip` (package management)
- `psutil` (optional helpers for runtime/process checks)

## Requirements

- Python **3.9+** recommended
- `pip` available in your Python installation
- Windows is the primary target; PySide6 supports Linux and macOS as well

Install runtime dependencies:

```bash
pip install PySide6 psutil
```

## Run

From the project folder:

```bash
python pipo.py
```

Theme preference is stored under `%LOCALAPPDATA%\Pipo\theme.json` on Windows (see [`pipo.py`](pipo.py) for other platforms).

## Building the Windows executable

Requires PyInstaller (and the dependencies above):

```bash
pip install pyinstaller PySide6 psutil
python -m PyInstaller --noconfirm pipo.spec
```

The windowed one-file build is written to **`dist/pipo.exe`**. Tagged releases may ship this artifact from [GitHub Releases](https://github.com/Shrekmachine/pipo/releases).

## How It Works

Pipo runs `pip` commands in the background and displays results in a GUI console panel.
It can mark packages with available updates and helps you upgrade them in a guided flow.

## Notes

- Package actions affect the Python environment used to run `pipo.py` (or the interpreter resolved when running the frozen `pipo.exe`).
- For virtual environments, activate the environment first, then start Pipo.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.
