# CaseLight

CaseLight is a focused Linux and Windows desktop controller for the Gigabyte
RGB Fusion 2.0 IT5711 case-light controller (`048D:5711`). Its hardware,
effects, and Linux spectrum code were isolated from Speechless, then rebuilt as
a standalone app with shared dual-boot state and Windows audio visualization.

## What is included

- Master brightness, all-on, and all-off controls
- 18 three-zone scenes and 12 exact solid colors
- Independent Case 1, Cooler, and Case 2 channel mapping
- Hardware pulse, flash, double-flash, and color-cycle modes
- Software breathing, rainbow, chase, police, ember, and aurora motion
- BPM-locked bounce, chase, and rainbow effects with tap tempo
- Six music styles with sensitivity, smoothing, minimum-glow, update-rate, and
  per-band gain controls
- Linux CAVA spectrum capture with a dependency-free PulseAudio FFT fallback
- Windows WASAPI loopback visualization through SoundCard
- Light timers, restore-on-open, and start-at-sign-in support
- Atomic state writes, a last-known-good backup, and one-time import of existing
  Speechless case-light settings

The interface uses a clean solid palette based on `#00212B`, exact black and
white, cyan, violet, and pink. There are no generated image assets or lossy UI
textures.

## Quick start

### Linux

Python 3.11+, Tk, and the system `hidapi` library are required. On Ubuntu or
Debian, install the platform packages if they are not already present:

```bash
sudo apt install python3-venv python3-tk libhidapi-hidraw0
./scripts/run-linux.sh
```

If Detect finds the controller but cannot open it, use **Settings → Install
Linux device access**. CaseLight shows an always-on-top explanation before the
system password prompt. The installer changes only the udev permission rule for
USB HID device `048D:5711`.

For music visualization, install CAVA (preferred) or PulseAudio tools:

```bash
sudo apt install cava pulseaudio-utils
```

### Windows

Install 64-bit Python 3.11+ with the Python launcher, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run-windows.ps1
```

The Windows environment installs `liquidctl`, NumPy, and SoundCard. The latter
two are loaded only while the music visualizer is active.

## Same state in Linux and Windows

CaseLight deliberately keeps state outside its application, source, build, and
extension directories.

When CaseLight is run from this shared drive, it finds the root of that physical
volume and stores its profile in:

```text
<shared-volume>/.caselight/state.json
<shared-volume>/.caselight/state.json.backup
```

Linux and Windows can mount the volume at completely different paths; because
the location is derived from the volume root, both copies still reach the same
profile. This is the simplest dual-boot setup: keep each packaged executable on
the shared volume and run it from there.

If the app is installed onto each operating system's local disk, open
**Settings → Choose shared folder** once in each OS and select the same folder
on the shared disk. Each OS keeps only a local pointer to that folder. You can
also launch with `--state-dir PATH` or set `CASELIGHT_STATE_DIR`.

**Start CaseLight when I sign in** writes one ordinary per-user startup entry.
The preference itself is shared, so CaseLight creates the equivalent entry when
it next runs under the other operating system. **Restore my last lighting
state** then reapplies the saved theme, zone map, effect, music mode, or off
state after login.

Writes use a same-directory temporary file and atomic replacement. Before each
replacement, the prior valid file is retained as `state.json.backup`. A broken
primary file is recovered from that backup automatically. Uninstalling or
replacing CaseLight never removes this profile.

## Build standalone executables

Builds must run on their target OS because PyInstaller is not a cross-compiler.

Linux:

```bash
./scripts/build-linux.sh
./dist/CaseLight
```

Windows PowerShell:

```powershell
.\scripts\build-windows.ps1
.\dist\CaseLight.exe
```

The GitHub Actions workflow also builds Linux and Windows artifacts from the
same revision.

## Test

The core is testable without the lighting controller or a live audio device:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers Speechless-state migration, brightness and color cleanup,
three-band FFT separation, every software and music frame, hardware command
validation, cross-platform startup files, atomic saves, and backup recovery.

## Hardware scope

Version 1.0 targets the exact controller used by Speechless:

- Vendor ID: `048D`
- Product ID: `5711`
- Driver: `liquidctl.driver.rgb_fusion2.RgbFusion2`
- Channels: `sync`, `led1` through `led8`

The app exposes all nine driver channels, while the initial physical mapping is
Case 1 → `led1`, Cooler → `led2`, and Case 2 → `led3`.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency attribution.
