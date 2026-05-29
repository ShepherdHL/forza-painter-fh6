# Hardware monitoring (external tools)

Forza Painter **does not include** an in-app hardware monitor. Earlier builds
used LibreHardwareMonitor, which triggered Microsoft Defender
(`VulnerableDriver:WinNT/Winring0`) because of the **WinRing0** driver family.

Use the tools below on your own PC if you want CPU/GPU temperature while
generating vinyls.

## Experimental eco GPU cooldown

The optional **GPU cooldown between images** (eco preset) needs a GPU
temperature. Without a bundled sensor stack it will:

- **Pause 30 seconds** between batch images when no GPU temperature is available, or
- Use temperature if you run a compatible external monitor that exposes data
  (not integrated today).

For reliable cooldown by temperature, watch GPU temp in an external tool and
pace your batch manually, or wait between runs.

## Recommended external tools (install separately)

Use any tool you trust. These are common on Windows and do not ship with
Forza Painter:

| Tool | Link | Good for |
| --- | --- | --- |
| **HWiNFO** | [hwinfo.com](https://www.hwinfo.com/) | CPU/GPU temps, logging, sensors |
| **GPU-Z** | [techpowerup.com/gpuz](https://www.techpowerup.com/gpuz/) | GPU temperature and clocks |
| **MSI Afterburner** | [msi.com/Landing/afterburner](https://www.msi.com/Landing/afterburner) | GPU temp overlay while gaming |
| **Windows Task Manager** | Built-in | Basic GPU utilization (Performance tab) |

**Note:** Some monitoring tools also use low-level drivers. If Defender
flags a driver, that is between you and that product’s vendor—not Forza Painter.

## Developers

- `scripts/fetch_librehardwaremonitor.ps1` is **deprecated** and not run by
  `install_dependencies.bat` or release builds.
- Do not re-enable LHM in `requirements.txt` or PyInstaller without addressing
  Defender’s vulnerable-driver blocklist.
