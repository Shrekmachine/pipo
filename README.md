# Pipo - Python Pip Manager Pro

Pipo is a desktop GUI tool for managing Python packages with `pip`.
It gives you a simple visual workflow to install, uninstall, inspect, and update packages without using terminal commands manually.

## Features

- View installed Python packages in a list
- Install new packages
- Uninstall selected packages
- Check for outdated packages
- Update all outdated packages in one flow
- Show package metadata (`pip show`)
- Show version history (`pip index versions`)

## Tech Stack

- Python 3
- Tkinter (GUI)
- `pip` (package management)
- `psutil` (process/runtime handling)

## Requirements

- Python 3.9+ recommended
- `pip` available in your Python installation
- Windows (primary target)

Install dependency:

```bash
pip install psutil
```

## Run

From the project folder:

```bash
python pipo.py
```

## How It Works

Pipo runs `pip` commands in the background and displays results in a GUI console panel.
It can mark packages with available updates and helps you upgrade them in a guided flow.

## Notes

- Package actions affect the Python environment used to run `pipo.py`.
- For virtual environments, activate the environment first, then start Pipo.

## License

Add your preferred license (for example, MIT) in a `LICENSE` file.
