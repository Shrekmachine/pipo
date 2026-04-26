import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import psutil
import os
import sys
import random
import json

def check_if_running():
    # Wir prüfen NUR, wenn das Programm als EXE läuft
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
    package_name = package_entry.get().strip()
    if not package_name:
        messagebox.showwarning("Input Error", "Please enter a package name.")
        return

    log_area.insert(tk.END, f"Installing {package_name}...\n")
    # WICHTIG: Erzwingt, dass Tkinter den Text sofort anzeigt,
    # bevor der blockierende Befehl startet
    root.update_idletasks()

    res = run_command(["install", package_name])

    # Fehlerprüfung: Falls res ein String ist (aus dem except-Block)
    output = res.stdout if hasattr(res, 'stdout') else str(res)
    log_area.insert(tk.END, output)

    if hasattr(res, 'returncode') and res.returncode == 0:
        messagebox.showinfo("Success", f"Installed {package_name}")
        refresh_list()

def refresh_list():
    """Fetches installed packages and populates the Listbox."""
    log_area.delete('1.0', tk.END)
    log_area.insert(tk.END, "Refreshing installed list...\n")
    root.update_idletasks() # Damit der User sieht, dass etwas passiert

    res = run_command(["list", "--format=freeze"])

    if hasattr(res, 'returncode') and res.returncode == 0:
        package_listbox.delete(0, tk.END)
        for line in res.stdout.splitlines():
            # Falls eine Zeile kein '==' hat (z.B. bei editable installs)
            name = line.split('==')[0]
            package_listbox.insert(tk.END, name)
        log_area.insert(tk.END, "List updated.\n")
    else:
        log_area.insert(tk.END, "Failed to fetch list.\n")

def uninstall_selected():
    selection = package_listbox.curselection()
    if not selection:
        messagebox.showwarning("Selection Error", "Please select a library first.")
        return

    package_name = package_listbox.get(selection[0])

    if messagebox.askyesno("Confirm", f"Are you sure you want to uninstall {package_name}?"):
        log_area.insert(tk.END, f"Uninstalling {package_name}...\n")
        res = run_command(["uninstall", "-y", package_name])
        log_area.insert(tk.END, res.stdout if hasattr(res, 'stdout') else res)
        refresh_list()

def show_details(show_warning=True):
    """Gets metadata for the selected library using 'pip show'."""
    selection = package_listbox.curselection()
    if not selection:
        if show_warning:
            messagebox.showwarning("Selection Error", "Click a library in the list to see its details.")
        return

    package_name = package_listbox.get(selection[0])
    log_area.delete('1.0', tk.END)
    log_area.insert(tk.END, f"--- Details for: {package_name} ---\n")

    # 'pip show' is the magic command for metadata
    res = run_command(["show", package_name])

    if hasattr(res, 'returncode') and res.returncode == 0:
        log_area.insert(tk.END, res.stdout)
    else:
        log_area.insert(tk.END, f"Could not find details for {package_name}.")

def on_package_select(event):
    """Automatically show details when a package is selected."""
    show_details(show_warning=False)

def check_updates():
    """Checks for outdated packages and shows available versions."""
    log_area.delete('1.0', tk.END)
    log_area.insert(tk.END, "Checking for package updates...\n")
    root.update_idletasks()

    res = run_command(["list", "--outdated", "--format=json"])

    if not hasattr(res, 'returncode') or res.returncode != 0:
        log_area.insert(tk.END, "Failed to check updates.\n")
        if hasattr(res, 'stdout') and res.stdout:
            log_area.insert(tk.END, res.stdout + "\n")
        if hasattr(res, 'stderr') and res.stderr:
            log_area.insert(tk.END, res.stderr + "\n")
        return

    try:
        outdated_packages = json.loads(res.stdout) if res.stdout.strip() else []
    except json.JSONDecodeError:
        log_area.insert(tk.END, "Could not parse update response.\n")
        log_area.insert(tk.END, res.stdout if hasattr(res, 'stdout') else "")
        return

    if not outdated_packages:
        log_area.insert(tk.END, "All packages are up to date.\n")
        return

    log_area.insert(tk.END, f"Found {len(outdated_packages)} package(s) with updates:\n\n")
    for pkg in outdated_packages:
        name = pkg.get("name", "unknown")
        current = pkg.get("version", "?")
        latest = pkg.get("latest_version", "?")
        log_area.insert(tk.END, f"- {name}: {current} -> {latest}\n")

# --- GUI Setup ---
if __name__ == "__main__":
    # Wenn das Programm schon läuft, beende den neuen Start sofort
    #if check_if_running():
        # Optional: Eine kurze Nachricht zeigen
        # ctypes.windll.user32.MessageBoxW(0, "Programm läuft bereits!", "Info", 0)
     #   sys.exit()

    # Erst hier startet dein eigentliches GUI-Programm
    root = tk.Tk()
    root.title("Python Pip Manager Pro")
    root.geometry("850x600")
    root.minsize(700, 500)

    # Main Header
    tk.Label(root, text="Python Pip Manager", font=("Arial", 16, "bold")).pack(pady=10)

    # Top Section: Install
    top_frame = tk.Frame(root)
    top_frame.pack(pady=10, fill='x', padx=20)
    tk.Label(top_frame, text="New Package:").pack(side=tk.LEFT)
    package_entry = tk.Entry(top_frame, font=("Arial", 11))
    package_entry.pack(side=tk.LEFT, padx=10, expand=True, fill='x')
    tk.Button(top_frame, text="Install", command=install_package, bg="#2E7D32", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

    # Middle Section: List and Log
    mid_frame = tk.Frame(root)
    mid_frame.pack(expand=True, fill='both', padx=20, pady=10)

    # Left Column
    list_container = tk.Frame(mid_frame)
    list_container.pack(side=tk.LEFT, fill='both', expand=False, padx=(0, 10))
    tk.Label(list_container, text="Installed Libraries:", font=("Arial", 10, "bold")).pack()
    package_listbox = tk.Listbox(list_container, width=35, font=("Arial", 10))
    package_listbox.pack(side=tk.LEFT, fill='both', expand=True)
    package_listbox.bind("<<ListboxSelect>>", on_package_select)
    list_scroll = tk.Scrollbar(list_container, command=package_listbox.yview)
    list_scroll.pack(side=tk.RIGHT, fill='y')
    package_listbox.config(yscrollcommand=list_scroll.set)

    # Right Column
    log_container = tk.Frame(mid_frame)
    log_container.pack(side=tk.RIGHT, fill='both', expand=True)
    tk.Label(log_container, text="Console Output:", font=("Arial", 10, "bold")).pack()
    log_area = scrolledtext.ScrolledText(log_container, font=("Consolas", 10), bg="#fdfdfd")
    log_area.pack(fill='both', expand=True)

    # Bottom Section: Action Buttons
    bottom_frame = tk.Frame(root)
    bottom_frame.pack(pady=20)

    # Button 1: Refresh
    tk.Button(bottom_frame, text="Refresh List", command=refresh_list, bg="#1976D2", fg="white", width=15).pack(side=tk.LEFT, padx=5)

    # Button 2: Details (New!)
    tk.Button(bottom_frame, text="Get Details", command=lambda: show_details(show_warning=True), bg="#607D8B", fg="white", width=15).pack(side=tk.LEFT, padx=5)

    # Button 3: Update Check
    tk.Button(bottom_frame, text="Check Updates", command=check_updates, bg="#F57C00", fg="white", width=15).pack(side=tk.LEFT, padx=5)

    # Button 4: Uninstall
    tk.Button(bottom_frame, text="Uninstall Selected", command=uninstall_selected, bg="#D32F2F", fg="white", width=15).pack(side=tk.LEFT, padx=5)

    # Initialize the list on startup
    refresh_list()

    root.mainloop()