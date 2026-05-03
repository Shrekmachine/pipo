import subprocess
import psutil
import os
import sys
import json

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QTextEdit,
    QMessageBox,
    QComboBox,
    QStyleFactory,
)
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor
from PySide6.QtCore import Qt

__version__ = "1.2.0"

UPDATE_MARKER_PREFIX = " [Update:"
outdated_versions = {}

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"
_THEME_KEYS = frozenset({THEME_SYSTEM, THEME_LIGHT, THEME_DARK})

# Populated in __main__ before any handlers run
root = None
package_entry = None
package_listbox = None
log_area = None
theme_selector = None


def _theme_settings_path():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        cfg = os.path.join(base, "Pipo")
    else:
        cfg = os.path.join(os.path.expanduser("~"), ".config", "Pipo")
    os.makedirs(cfg, exist_ok=True)
    return os.path.join(cfg, "theme.json")


def _load_theme_setting():
    path = _theme_settings_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        mode = data.get("theme", THEME_SYSTEM)
        return mode if mode in _THEME_KEYS else THEME_SYSTEM
    except (OSError, json.JSONDecodeError, TypeError):
        return THEME_SYSTEM


def _save_theme_setting(mode):
    if mode not in _THEME_KEYS:
        return
    path = _theme_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"theme": mode}, f)
    except OSError:
        pass


def _system_prefers_dark(app):
    hints = app.styleHints()
    scheme = hints.colorScheme()
    cs = getattr(Qt, "ColorScheme", None)
    if cs is not None:
        if scheme == cs.Dark:
            return True
        if scheme == cs.Light:
            return False
    return False


def _palette_light():
    p = QPalette()
    window = QColor(240, 240, 240)
    base = QColor(255, 255, 255)
    text = QColor(0, 0, 0)
    button = QColor(240, 240, 240)
    highlight = QColor(66, 139, 202)

    p.setColor(QPalette.ColorRole.Window, window)
    p.setColor(QPalette.ColorRole.WindowText, text)
    p.setColor(QPalette.ColorRole.Base, base)
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(233, 233, 233))
    p.setColor(QPalette.ColorRole.Text, text)
    p.setColor(QPalette.ColorRole.Button, button)
    p.setColor(QPalette.ColorRole.ButtonText, text)
    p.setColor(QPalette.ColorRole.Highlight, highlight)
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
    disabled = QColor(120, 120, 120)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
    return p


def _palette_dark():
    p = QPalette()
    window = QColor(53, 53, 53)
    base = QColor(42, 42, 42)
    alt = QColor(66, 66, 66)
    text = QColor(212, 212, 212)
    disabled_text = QColor(127, 127, 127)
    highlight = QColor(42, 130, 218)
    button = QColor(53, 53, 53)

    p.setColor(QPalette.ColorRole.Window, window)
    p.setColor(QPalette.ColorRole.WindowText, text)
    p.setColor(QPalette.ColorRole.Base, base)
    p.setColor(QPalette.ColorRole.AlternateBase, alt)
    p.setColor(QPalette.ColorRole.ToolTipBase, window)
    p.setColor(QPalette.ColorRole.ToolTipText, text)
    p.setColor(QPalette.ColorRole.Text, text)
    p.setColor(QPalette.ColorRole.Button, button)
    p.setColor(QPalette.ColorRole.ButtonText, text)
    p.setColor(QPalette.ColorRole.BrightText, QColor(255, 100, 100))
    p.setColor(QPalette.ColorRole.Link, highlight)
    p.setColor(QPalette.ColorRole.Highlight, highlight)
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text)
    return p


def _use_dark_palette(app, mode):
    if mode == THEME_SYSTEM:
        return _system_prefers_dark(app)
    if mode == THEME_DARK:
        return True
    return False


def _apply_fusion_style(app):
    style = QStyleFactory.create("Fusion")
    if style is not None:
        app.setStyle(style)


def apply_theme(mode):
    """Apply light/dark palette. Call with THEME_* after QApplication exists."""
    app = QApplication.instance()
    if app is None:
        return
    if mode not in _THEME_KEYS:
        mode = THEME_SYSTEM
    dark = _use_dark_palette(app, mode)
    app.setPalette(_palette_dark() if dark else _palette_light())


def _on_os_color_scheme_changed():
    if theme_selector is None:
        return
    mode = theme_selector.currentData()
    if mode != THEME_SYSTEM:
        return
    apply_theme(THEME_SYSTEM)


def _on_theme_combo_changed():
    if theme_selector is None:
        return
    mode = theme_selector.currentData()
    apply_theme(mode)
    _save_theme_setting(mode)


def _log_insert(text):
    cursor = log_area.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText(text)
    log_area.setTextCursor(cursor)


def check_if_running():
    # Wir prüfen NUR, wenn das Programm als EXE läuft..
    # (getattr(sys, 'frozen', False) prüft, ob es eine PyInstaller EXE ist)
    if not getattr(sys, 'frozen', False):
        return False

    current_pid = os.getpid()
    my_name = os.path.basename(sys.executable).lower()

    try:
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                # Name auf Kleinschreibung prüfen für Windows-Stabilität
                if proc.info['name'].lower() == my_name and proc.info['pid'] != current_pid:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        # Falls psutil komplett blockiert wird, lieber starten als gar nichts tun
        return False
    return False


def run_command(command_list):
    """Helper to run pip commands and return output."""

    # DER FIX: Wenn kompiliert, nutze "python", ansonsten nutze sys.executable
    if getattr(sys, 'frozen', False):
        python_cmd = "python"
    else:
        python_cmd = sys.executable

    try:
        process = subprocess.run(
            [python_cmd, "-m", "pip"] + command_list,
            capture_output=True,
            text=True,
            # Profi-Tipp: Das verhindert, dass bei jedem Klick ein schwarzes Fenster aufblitzt
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return process
    except Exception as e:
        return str(e)


def install_package():
    package_name = package_entry.text().strip()
    if not package_name:
        QMessageBox.warning(root, "Input Error", "Please enter a package name.")
        return

    _log_insert(f"Installing {package_name}...\n")
    QApplication.processEvents()

    res = run_command(["install", package_name])

    # Fehlerprüfung: Falls res ein String ist (aus dem except-Block)
    output = res.stdout if hasattr(res, 'stdout') else str(res)
    _log_insert(output)

    if hasattr(res, 'returncode') and res.returncode == 0:
        QMessageBox.information(root, "Success", f"Installed {package_name}")
        refresh_list(check_for_updates=True)


def fetch_outdated_packages(show_errors=True):
    """Returns outdated packages as {name: (current_version, latest_version)}."""
    res = run_command(["list", "--outdated", "--format=json"])

    if not hasattr(res, 'returncode') or res.returncode != 0:
        if show_errors:
            _log_insert("Failed to check updates.\n")
            if hasattr(res, 'stdout') and res.stdout:
                _log_insert(res.stdout + "\n")
            if hasattr(res, 'stderr') and res.stderr:
                _log_insert(res.stderr + "\n")
        return None

    try:
        outdated_list = json.loads(res.stdout) if res.stdout.strip() else []
    except json.JSONDecodeError:
        if show_errors:
            _log_insert("Could not parse update response.\n")
            _log_insert(res.stdout if hasattr(res, 'stdout') else "")
        return None

    return {
        pkg.get("name", ""): (pkg.get("version", "?"), pkg.get("latest_version", "?"))
        for pkg in outdated_list
        if pkg.get("name")
    }


def get_selected_package_name(show_warning=True):
    """Returns selected package base name from listbox marker text."""
    row = package_listbox.currentRow()
    if row < 0:
        if show_warning:
            QMessageBox.warning(root, "Selection Error", "Please select a library first.")
        return None

    display_name = package_listbox.item(row).text()
    if UPDATE_MARKER_PREFIX in display_name:
        return display_name.split(UPDATE_MARKER_PREFIX, 1)[0].strip()
    return display_name


def refresh_list(check_for_updates=False):
    """Fetches installed packages and populates the Listbox."""
    log_area.clear()
    if check_for_updates:
        _log_insert("Refreshing installed list and checking updates...\n")
    else:
        _log_insert("Refreshing installed list...\n")
    QApplication.processEvents()

    global outdated_versions
    if check_for_updates:
        outdated_data = fetch_outdated_packages(show_errors=False)
        outdated_versions = outdated_data if outdated_data is not None else {}

    res = run_command(["list", "--format=freeze"])

    if hasattr(res, 'returncode') and res.returncode == 0:
        package_listbox.blockSignals(True)
        package_listbox.clear()
        for line in res.stdout.splitlines():
            # Falls eine Zeile kein '==' hat (z.B. bei editable installs)
            name = line.split('==')[0]
            if name in outdated_versions:
                current, latest = outdated_versions[name]
                display_name = f"{name} [Update: {current} -> {latest}]"
            else:
                display_name = name
            package_listbox.addItem(display_name)
        package_listbox.blockSignals(False)
        _log_insert("List updated.\n")
        if check_for_updates and outdated_versions:
            _log_insert(f"{len(outdated_versions)} update(s) marked in Installed Libraries.\n")
    else:
        _log_insert("Failed to fetch list.\n")


def uninstall_selected():
    package_name = get_selected_package_name(show_warning=True)
    if not package_name:
        return

    reply = QMessageBox.question(
        root,
        "Confirm",
        f"Are you sure you want to uninstall {package_name}?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    _log_insert(f"Uninstalling {package_name}...\n")
    res = run_command(["uninstall", "-y", package_name])
    _log_insert(res.stdout if hasattr(res, 'stdout') else str(res))
    refresh_list(check_for_updates=True)


def show_details(show_warning=True, package_name=None):
    """Gets metadata for the selected library using 'pip show'."""
    if package_name is None:
        package_name = get_selected_package_name(show_warning=show_warning)
    if not package_name:
        if show_warning:
            QMessageBox.warning(
                root,
                "Selection Error",
                "Click a library in the list to see its details.",
            )
        return

    log_area.clear()
    _log_insert(f"--- Details for: {package_name} ---\n")

    # 'pip show' is the magic command for metadata
    res = run_command(["show", package_name])

    if hasattr(res, 'returncode') and res.returncode == 0:
        _log_insert(res.stdout)
    else:
        _log_insert(f"Could not find details for {package_name}.")


def show_version_history(package_name):
    """Shows available versions for the selected package."""
    log_area.clear()
    _log_insert(f"--- Version History for: {package_name} ---\n")

    res = run_command(["index", "versions", package_name])
    output = res.stdout if hasattr(res, 'stdout') else str(res)

    if hasattr(res, 'returncode') and res.returncode == 0:
        _log_insert(output if output.strip() else "No version history output returned.\n")
    else:
        _log_insert("Could not fetch version history.\n")
        if output:
            _log_insert(output + "\n")
        if hasattr(res, 'stderr') and res.stderr:
            _log_insert(res.stderr + "\n")


def on_package_select():
    """Shows version history for outdated packages, otherwise package details."""
    package_name = get_selected_package_name(show_warning=False)
    if not package_name:
        return
    if package_name in outdated_versions:
        show_version_history(package_name)
    else:
        show_details(show_warning=False, package_name=package_name)


def check_updates():
    """Checks for outdated packages and offers to update them."""
    log_area.clear()
    _log_insert("Checking for package updates...\n")
    QApplication.processEvents()

    outdated_data = fetch_outdated_packages(show_errors=True)
    if outdated_data is None:
        return

    if not outdated_data:
        _log_insert("All packages are up to date.\n")
        refresh_list(check_for_updates=True)
        return

    _log_insert(f"Found {len(outdated_data)} package(s) with updates:\n\n")
    for name, (current, latest) in outdated_data.items():
        _log_insert(f"- {name}: {current} -> {latest}\n")
    package_names = list(outdated_data.keys())
    package_count = len(package_names)
    reply = QMessageBox.question(
        root,
        "Updates Found",
        f"Found updates for {package_count} package(s).\nDo you want to update all of them now?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        _log_insert("\nUpdate cancelled by user.\n")
        return

    _log_insert("\nStarting updates...\n")

    successful_updates = 0
    for package_name in package_names:
        _log_insert(f"Updating {package_name}...\n")
        QApplication.processEvents()
        upgrade_res = run_command(["install", "--upgrade", package_name])
        _log_insert(
            upgrade_res.stdout if hasattr(upgrade_res, 'stdout') else str(upgrade_res)
        )
        if hasattr(upgrade_res, 'returncode') and upgrade_res.returncode == 0:
            successful_updates += 1
        elif hasattr(upgrade_res, 'stderr') and upgrade_res.stderr:
            _log_insert(upgrade_res.stderr + "\n")

    _log_insert(
        f"\nUpdate complete: {successful_updates}/{package_count} package(s) updated successfully.\n"
    )
    refresh_list(check_for_updates=True)


def _styled_button(text, bg_hex, handler, bold=False):
    btn = QPushButton(text)
    btn.clicked.connect(handler)
    weight = "bold" if bold else "normal"
    btn.setStyleSheet(f"background-color: {bg_hex}; color: white; font-weight: {weight}; padding: 6px 12px;")
    btn.setMinimumWidth(130)
    return btn


# --- GUI Setup ---
if __name__ == "__main__":
    # Wenn das Programm schon läuft, beende den neuen Start sofort
    # if check_if_running():
    #     sys.exit()

    app = QApplication(sys.argv)

    saved_theme = _load_theme_setting()
    _apply_fusion_style(app)
    apply_theme(saved_theme)

    hints = app.styleHints()
    if hasattr(hints, "colorSchemeChanged"):
        hints.colorSchemeChanged.connect(_on_os_color_scheme_changed)

    root = QWidget()
    root.setWindowTitle(f"Python Pip Manager Pro v{__version__}")
    root.resize(850, 600)
    root.setMinimumSize(700, 500)

    main_layout = QVBoxLayout(root)

    theme_row = QHBoxLayout()
    theme_row.addStretch()
    theme_row.addWidget(QLabel("Theme:"))
    theme_selector = QComboBox()
    theme_selector.addItem("System", THEME_SYSTEM)
    theme_selector.addItem("Light", THEME_LIGHT)
    theme_selector.addItem("Dark", THEME_DARK)
    idx = theme_selector.findData(saved_theme)
    theme_selector.setCurrentIndex(idx if idx >= 0 else 0)
    theme_selector.currentIndexChanged.connect(lambda _i: _on_theme_combo_changed())
    theme_row.addWidget(theme_selector)
    main_layout.addLayout(theme_row)

    title = QLabel("Python Pip Manager")
    title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(title)

    top_row = QHBoxLayout()
    top_row.addWidget(QLabel("New Package:"))
    package_entry = QLineEdit()
    package_entry.setFont(QFont("Arial", 11))
    top_row.addWidget(package_entry, stretch=1)
    top_row.addWidget(_styled_button("Install", "#2E7D32", install_package, bold=True))
    main_layout.addLayout(top_row)

    mid_row = QHBoxLayout()

    list_col = QVBoxLayout()
    list_label = QLabel("Installed Libraries:")
    list_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    list_col.addWidget(list_label)
    package_listbox = QListWidget()
    package_listbox.setFont(QFont("Arial", 10))
    package_listbox.setMinimumWidth(280)
    package_listbox.itemSelectionChanged.connect(on_package_select)
    list_col.addWidget(package_listbox)
    mid_row.addLayout(list_col)

    log_col = QVBoxLayout()
    log_label = QLabel("Console Output:")
    log_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    log_col.addWidget(log_label)
    log_area = QTextEdit()
    log_area.setReadOnly(True)
    log_area.setFont(QFont("Consolas", 10))
    # Theme-aware: fixed light (#fdfdfd) bg forced light-on-light text under Windows dark mode.
    log_area.setStyleSheet(
        """
        QTextEdit {
            background-color: palette(base);
            color: palette(text);
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
        }
        """
    )
    log_col.addWidget(log_area)
    mid_row.addLayout(log_col, stretch=1)

    main_layout.addLayout(mid_row, stretch=1)

    bottom_row = QHBoxLayout()
    bottom_row.addStretch()
    bottom_row.addWidget(
        _styled_button(
            "Refresh List",
            "#1976D2",
            lambda: refresh_list(check_for_updates=True),
        )
    )
    bottom_row.addWidget(_styled_button("Check Updates", "#F57C00", check_updates))
    bottom_row.addWidget(_styled_button("Uninstall Selected", "#D32F2F", uninstall_selected))
    bottom_row.addStretch()
    main_layout.addLayout(bottom_row)

    refresh_list(check_for_updates=True)

    root.show()
    sys.exit(app.exec())
