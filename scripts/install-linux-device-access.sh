#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RULE_SOURCE="${PROJECT_DIR}/udev/60-caselight-gigabyte.rules"
RULE_TARGET="/etc/udev/rules.d/60-caselight-gigabyte.rules"

python3 - <<'PY'
import tkinter as tk
from tkinter import messagebox

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
messagebox.showinfo(
    "CaseLight administrator access",
    "A system password prompt will open next. Access is needed only to install the USB permission rule for Gigabyte device 048D:5711 and reload udev.",
    parent=root,
)
root.destroy()
PY
pkexec sh -c 'install -m 0644 "$1" "$2" && udevadm control --reload-rules && udevadm trigger --subsystem-match=hidraw' sh "${RULE_SOURCE}" "${RULE_TARGET}"

python3 - <<'PY'
import tkinter as tk
from tkinter import messagebox

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
messagebox.showinfo(
    "CaseLight device access installed",
    "The USB rule is installed. Unplug and reconnect the lighting controller, then press Detect in CaseLight.",
    parent=root,
)
root.destroy()
PY
