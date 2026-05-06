import json
import os
import subprocess
import sys
from dataclasses import dataclass

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPalette, QTextCursor
from PySide6.QtWidgets import (
    QMenu,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QStyleFactory,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

__version__ = "1.4.0"

UPDATE_MARKER_PREFIX = " [Update:"

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"
_THEME_KEYS = frozenset({THEME_SYSTEM, THEME_LIGHT, THEME_DARK})


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    error: str = ""

    @property
    def ok(self):
        return self.returncode == 0 and not self.error


class PipCommandThread(QThread):
    result_ready = Signal(object)

    def __init__(self, command_list, parent=None):
        super().__init__(parent)
        self.command_list = command_list

    def run(self):
        self.result_ready.emit(run_command(self.command_list))


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
    app = QApplication.instance()
    if app is None:
        return
    if mode not in _THEME_KEYS:
        mode = THEME_SYSTEM
    dark = _use_dark_palette(app, mode)
    app.setPalette(_palette_dark() if dark else _palette_light())


def run_command(command_list):
    if getattr(sys, "frozen", False):
        python_cmd = "python"
    else:
        python_cmd = sys.executable

    try:
        process = subprocess.run(
            [python_cmd, "-m", "pip"] + command_list,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return CommandResult(
            returncode=process.returncode,
            stdout=process.stdout or "",
            stderr=process.stderr or "",
        )
    except Exception as e:
        return CommandResult(returncode=1, error=str(e))


class PipoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.outdated_versions = {}
        self._action_busy = False
        self._detail_busy = False
        self._threads = set()
        self._pending_updates = []
        self._successful_updates = 0
        self._total_updates = 0
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle(f"Python Pip Manager Pro v{__version__}")
        self.resize(850, 600)
        self.setMinimumSize(700, 500)

        main_layout = QVBoxLayout(self)

        theme_row = QHBoxLayout()
        theme_row.addStretch()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_selector = QComboBox()
        self.theme_selector.addItem("System", THEME_SYSTEM)
        self.theme_selector.addItem("Light", THEME_LIGHT)
        self.theme_selector.addItem("Dark", THEME_DARK)
        saved_theme = _load_theme_setting()
        idx = self.theme_selector.findData(saved_theme)
        self.theme_selector.setCurrentIndex(idx if idx >= 0 else 0)
        self.theme_selector.currentIndexChanged.connect(self._on_theme_combo_changed)
        main_layout.addLayout(theme_row)
        theme_row.addWidget(self.theme_selector)

        title = QLabel("Python Pip Manager")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("New Package:"))
        self.package_entry = QLineEdit()
        self.package_entry.setFont(QFont("Arial", 11))
        top_row.addWidget(self.package_entry, stretch=1)
        self.install_btn = self._styled_button("Install", "#2E7D32", self.install_package, bold=True)
        top_row.addWidget(self.install_btn)
        main_layout.addLayout(top_row)

        mid_row = QHBoxLayout()

        list_col = QVBoxLayout()
        list_label = QLabel("Installed Libraries:")
        list_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        list_col.addWidget(list_label)
        self.package_listbox = QListWidget()
        self.package_listbox.setFont(QFont("Arial", 10))
        self.package_listbox.setMinimumWidth(280)
        self.package_listbox.itemSelectionChanged.connect(self.on_package_select)
        self.package_listbox.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.package_listbox.customContextMenuRequested.connect(self._show_package_context_menu)
        list_col.addWidget(self.package_listbox)
        mid_row.addLayout(list_col)

        log_col = QVBoxLayout()
        log_label = QLabel("Console Output:")
        log_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        log_col.addWidget(log_label)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 10))
        self.log_area.setStyleSheet(
            """
            QTextEdit {
                background-color: palette(base);
                color: palette(text);
                selection-background-color: palette(highlight);
                selection-color: palette(highlighted-text);
            }
            """
        )
        log_col.addWidget(self.log_area)
        mid_row.addLayout(log_col, stretch=1)
        main_layout.addLayout(mid_row, stretch=1)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.refresh_btn = self._styled_button("Refresh List", "#1976D2", self._refresh_button_clicked)
        self.update_selected_btn = self._styled_button("Update Selected", "#6A1B9A", self.update_selected)
        self.update_all_btn = self._styled_button("Update All Outdated", "#F57C00", self.update_all_outdated)
        self.uninstall_btn = self._styled_button("Uninstall Selected", "#D32F2F", self.uninstall_selected)
        bottom_row.addWidget(self.refresh_btn)
        bottom_row.addWidget(self.update_selected_btn)
        bottom_row.addWidget(self.update_all_btn)
        bottom_row.addWidget(self.uninstall_btn)
        bottom_row.addStretch()
        main_layout.addLayout(bottom_row)

    def _refresh_button_clicked(self):
        self.refresh_list(check_for_updates=True)

    def _styled_button(self, text, bg_hex, handler, bold=False):
        btn = QPushButton(text)
        btn.clicked.connect(handler)
        weight = "bold" if bold else "normal"
        btn.setStyleSheet(
            f"background-color: {bg_hex}; color: white; font-weight: {weight}; padding: 6px 12px;"
        )
        btn.setMinimumWidth(130)
        return btn

    def _on_theme_combo_changed(self):
        mode = self.theme_selector.currentData()
        apply_theme(mode)
        _save_theme_setting(mode)

    def on_os_color_scheme_changed(self):
        mode = self.theme_selector.currentData()
        if mode == THEME_SYSTEM:
            apply_theme(THEME_SYSTEM)

    def _set_action_busy(self, busy):
        self._action_busy = busy
        self.install_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)
        self.update_selected_btn.setEnabled(not busy)
        self.update_all_btn.setEnabled(not busy)
        self.uninstall_btn.setEnabled(not busy)
        self.package_entry.setEnabled(not busy)

    def _set_detail_busy(self, busy):
        self._detail_busy = busy

    def _log_insert(self, text):
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.log_area.setTextCursor(cursor)

    def _log_result(self, result):
        if result.error:
            self._log_insert(result.error + "\n")
        if result.stdout:
            self._log_insert(result.stdout)
            if not result.stdout.endswith("\n"):
                self._log_insert("\n")
        if result.stderr:
            self._log_insert(result.stderr)
            if not result.stderr.endswith("\n"):
                self._log_insert("\n")

    def _run_pip_async(self, command_list, callback):
        thread = PipCommandThread(command_list, self)
        self._threads.add(thread)

        def on_done(result):
            callback(result)
            self._threads.discard(thread)
            thread.deleteLater()

        thread.result_ready.connect(on_done)
        thread.start()

    def _parse_outdated_result(self, result, show_errors):
        if not result.ok:
            if show_errors:
                self._log_insert("Failed to check updates.\n")
                self._log_result(result)
            return None
        try:
            outdated_list = json.loads(result.stdout) if result.stdout.strip() else []
        except json.JSONDecodeError:
            if show_errors:
                self._log_insert("Could not parse update response.\n")
                self._log_insert(result.stdout + "\n")
            return None
        return {
            pkg.get("name", ""): (pkg.get("version", "?"), pkg.get("latest_version", "?"))
            for pkg in outdated_list
            if pkg.get("name")
        }

    def _extract_installed_latest(self, text):
        installed = None
        latest = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith("INSTALLED:"):
                installed = line.split(":", 1)[1].strip()
            elif line.startswith("LATEST:"):
                latest = line.split(":", 1)[1].strip()
        return installed, latest

    def get_selected_package_name(self, show_warning=True):
        row = self.package_listbox.currentRow()
        if row < 0:
            if show_warning:
                QMessageBox.warning(self, "Selection Error", "Please select a library first.")
            return None
        display_name = self.package_listbox.item(row).text()
        if UPDATE_MARKER_PREFIX in display_name:
            return display_name.split(UPDATE_MARKER_PREFIX, 1)[0].strip()
        return display_name

    def refresh_list(self, check_for_updates=False):
        self.log_area.clear()
        self._log_insert(
            "Refreshing installed list and checking updates...\n"
            if check_for_updates
            else "Refreshing installed list...\n"
        )
        self._set_action_busy(True)
        if check_for_updates:
            self._run_pip_async(["list", "--outdated", "--format=json"], self._on_refresh_outdated_ready)
        else:
            self._run_pip_async(["list", "--format=freeze"], self._on_refresh_list_ready)

    def _on_refresh_outdated_ready(self, result):
        data = self._parse_outdated_result(result, show_errors=False)
        self.outdated_versions = data if data is not None else {}
        self._run_pip_async(["list", "--format=freeze"], self._on_refresh_list_ready)

    def _on_refresh_list_ready(self, result):
        if result.ok:
            self.package_listbox.blockSignals(True)
            self.package_listbox.clear()
            for line in result.stdout.splitlines():
                name = line.split("==")[0]
                if name in self.outdated_versions:
                    current, latest = self.outdated_versions[name]
                    display_name = f"{name} [Update: {current} -> {latest}]"
                else:
                    display_name = name
                self.package_listbox.addItem(display_name)
            self.package_listbox.blockSignals(False)
            self._log_insert("List updated.\n")
            if self.outdated_versions:
                self._log_insert(f"{len(self.outdated_versions)} update(s) marked in Installed Libraries.\n")
        else:
            self._log_insert("Failed to fetch list.\n")
            self._log_result(result)
        self._set_action_busy(False)

    def install_package(self):
        package_name = self.package_entry.text().strip()
        if not package_name:
            QMessageBox.warning(self, "Input Error", "Please enter a package name.")
            return
        self._set_action_busy(True)
        self._log_insert(f"Installing {package_name}...\n")

        def done(result):
            self._log_result(result)
            self._set_action_busy(False)
            if result.ok:
                QMessageBox.information(self, "Success", f"Installed {package_name}")
                self.refresh_list(check_for_updates=True)

        self._run_pip_async(["install", package_name], done)

    def uninstall_selected(self):
        package_name = self.get_selected_package_name(show_warning=True)
        if not package_name:
            return
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Are you sure you want to uninstall {package_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._set_action_busy(True)
        self._log_insert(f"Uninstalling {package_name}...\n")

        def done(result):
            self._log_result(result)
            self._set_action_busy(False)
            self.refresh_list(check_for_updates=True)

        self._run_pip_async(["uninstall", "-y", package_name], done)

    def show_details(self, show_warning=True, package_name=None):
        if package_name is None:
            package_name = self.get_selected_package_name(show_warning=show_warning)
        if not package_name:
            if show_warning:
                QMessageBox.warning(
                    self,
                    "Selection Error",
                    "Click a library in the list to see its details.",
                )
            return
        self.log_area.clear()
        self._log_insert(f"--- Details for: {package_name} ---\n")
        self._set_detail_busy(True)

        def done(result):
            if result.ok:
                self._log_insert(result.stdout)
                if result.stderr:
                    self._log_insert(result.stderr)
            else:
                self._log_insert(f"Could not find details for {package_name}.\n")
                self._log_result(result)
            self._set_detail_busy(False)

        self._run_pip_async(["show", package_name], done)

    def show_version_history(self, package_name):
        self.log_area.clear()
        self._log_insert(f"--- Version History for: {package_name} ---\n")
        self._set_detail_busy(True)

        def done(result):
            if result.ok:
                output = result.stdout if result.stdout.strip() else "No version history output returned.\n"
                self._log_insert(output)
                installed, latest = self._extract_installed_latest(result.stdout)
                if installed and latest and installed == latest:
                    self._log_insert(f"\nNo update found for {package_name}.\n")
                    QMessageBox.information(self, "No Update Found", f"No update found for {package_name}.")
            else:
                self._log_insert("Could not fetch version history.\n")
                self._log_result(result)
            self._set_detail_busy(False)

        self._run_pip_async(["index", "versions", package_name], done)

    def on_package_select(self):
        if self._detail_busy:
            return
        package_name = self.get_selected_package_name(show_warning=False)
        if not package_name:
            return
        if package_name in self.outdated_versions:
            self.show_version_history(package_name)
        else:
            self.show_details(show_warning=False, package_name=package_name)

    def _show_package_context_menu(self, pos):
        item = self.package_listbox.itemAt(pos)
        if item is None or self._action_busy:
            return
        self.package_listbox.setCurrentItem(item)
        package_name = self.get_selected_package_name(show_warning=False)
        if not package_name:
            return

        menu = QMenu(self)
        update_action = menu.addAction("Update Selected")
        history_action = menu.addAction("Show History")
        chosen = menu.exec(self.package_listbox.mapToGlobal(pos))
        if chosen == update_action:
            self.update_selected()
        elif chosen == history_action:
            self.show_version_history(package_name)

    def _start_bulk_update(self, package_names):
        if not package_names:
            self._set_action_busy(False)
            return
        self._log_insert("\nStarting updates...\n")
        self._pending_updates = package_names
        self._successful_updates = 0
        self._total_updates = len(package_names)
        self._update_next_package()

    def update_all_outdated(self):
        self.log_area.clear()
        self._log_insert("Checking for outdated packages...\n")
        self._set_action_busy(True)
        self._run_pip_async(["list", "--outdated", "--format=json"], self._on_update_all_outdated_ready)

    def _on_update_all_outdated_ready(self, result):
        outdated_data = self._parse_outdated_result(result, show_errors=True)
        if outdated_data is None:
            self._set_action_busy(False)
            return
        self.outdated_versions = outdated_data
        if not outdated_data:
            self._log_insert("All packages are up to date.\n")
            self._set_action_busy(False)
            self.refresh_list(check_for_updates=True)
            return

        self._log_insert(f"Found {len(outdated_data)} package(s) with updates:\n\n")
        for name, (current, latest) in outdated_data.items():
            self._log_insert(f"- {name}: {current} -> {latest}\n")
        package_names = list(outdated_data.keys())
        package_count = len(package_names)
        reply = QMessageBox.question(
            self,
            "Updates Found",
            f"Found updates for {package_count} package(s).\nDo you want to update all of them now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._log_insert("\nUpdate cancelled by user.\n")
            self._set_action_busy(False)
            return

        self._start_bulk_update(package_names)

    def update_selected(self):
        package_name = self.get_selected_package_name(show_warning=True)
        if not package_name:
            return
        self.log_area.clear()
        self._log_insert(f"Checking if {package_name} has an update...\n")
        self._set_action_busy(True)
        self._run_pip_async(
            ["list", "--outdated", "--format=json"],
            lambda result: self._on_update_selected_outdated_ready(result, package_name),
        )

    def _on_update_selected_outdated_ready(self, result, package_name):
        outdated_data = self._parse_outdated_result(result, show_errors=True)
        if outdated_data is None:
            self._set_action_busy(False)
            return
        self.outdated_versions = outdated_data
        if package_name not in outdated_data:
            self._log_insert(f"No update found for {package_name}.\n")
            QMessageBox.information(self, "No Update Found", f"No update found for {package_name}.")
            self._set_action_busy(False)
            self.refresh_list(check_for_updates=True)
            return

        current, latest = outdated_data[package_name]
        reply = QMessageBox.question(
            self,
            "Update Selected Package",
            f"Update {package_name} from {current} to {latest}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._log_insert("\nUpdate cancelled by user.\n")
            self._set_action_busy(False)
            return
        self._start_bulk_update([package_name])

    def _update_next_package(self):
        if not self._pending_updates:
            self._log_insert(
                f"\nUpdate complete: {self._successful_updates}/{self._total_updates} package(s) updated successfully.\n"
            )
            self._set_action_busy(False)
            self.refresh_list(check_for_updates=True)
            return
        package_name = self._pending_updates.pop(0)
        self._log_insert(f"Updating {package_name}...\n")

        def done(result):
            self._log_result(result)
            if result.ok:
                self._successful_updates += 1
            self._update_next_package()

        self._run_pip_async(["install", "--upgrade", package_name], done)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    saved_theme = _load_theme_setting()
    _apply_fusion_style(app)
    apply_theme(saved_theme)

    window = PipoWindow()

    hints = app.styleHints()
    if hasattr(hints, "colorSchemeChanged"):
        hints.colorSchemeChanged.connect(window.on_os_color_scheme_changed)

    window.refresh_list(check_for_updates=True)
    window.show()
    sys.exit(app.exec())
