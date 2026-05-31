# Hardware monitoring

Forza Painter includes a **header Resource Monitor** (CPU/GPU load, clock, and
temperature) when enabled. GPU temperature and load for the selected card come
from **MSI Afterburner** shared memory when Afterburner is running.

LibreHardwareMonitor is **not** bundled. Earlier experiments used LHM, which
triggered Microsoft Defender (`VulnerableDriver:WinNT/Winring0`) because of the
**WinRing0** driver family.

## In-app Resource Monitor

When the monitor is enabled you will see:

- CPU and GPU donuts (or compact text on narrow windows)
- Green / yellow / red temperature coloring (80°C / 90°C thresholds)
- Heat warning banners and log lines when thresholds are crossed
- **Monitor GPU** — choose which adapter to watch and use for generation routing
- **Backend** — Auto, OpenCL, or Vulkan for the bundled generator
- **↻** — refresh the detected GPU list

### MSI Afterburner (recommended for GPU temperature)

1. Install [MSI Afterburner](https://www.msi.com/Landing/afterburner).
2. Keep Afterburner **running** while generating (tray icon is fine).
3. Pick your card in **Monitor GPU** if you have multiple GPUs.

If Afterburner is not running, GPU temperature may show as unavailable; CPU
metrics still work via platform APIs where supported.

## Experimental eco GPU cooldown

The optional **GPU cooldown between images** (eco preset) uses the **Monitor GPU**
selection for temperature when sensors are available:

- **≤75°C** — continue to the next image when MSI Afterburner reports the selected GPU at or below target
- **No sensor** — fixed **30 second** pause between batch images

## Multi-GPU generation routing

See **[GPU_GENERATION.md](GPU_GENERATION.md)** for how Monitor GPU, Backend, Windows
GPU preference, and future `-gpu-id` binding work together.

## Optional external tools

Use any tool you trust for overlays, logging, or extra sensors. These do **not**
ship with Forza Painter:

| Tool | Link | Good for |
| --- | --- | --- |
| **HWiNFO** | [hwinfo.com](https://www.hwinfo.com/) | CPU/GPU temps, logging, sensors |
| **GPU-Z** | [techpowerup.com/gpuz](https://www.techpowerup.com/gpuz/) | GPU temperature and clocks |
| **MSI Afterburner** | [msi.com/Landing/afterburner](https://www.msi.com/Landing/afterburner) | GPU temp overlay; also feeds the in-app monitor |
| **Windows Task Manager** | Built-in | Basic GPU utilization (Performance tab) |

**Note:** Some monitoring tools use low-level drivers. If Defender flags a driver,
that is between you and that product’s vendor—not Forza Painter.

## Developers

- `scripts/fetch_librehardwaremonitor.ps1` is **deprecated** and not run by
  `install_dependencies.bat` or release builds.
- Do not re-enable LHM in `requirements.txt` or PyInstaller without addressing
  Defender’s vulnerable-driver blocklist.
- GPU adapter enumeration: `src/gpu_adapters.py` (WMI + Afterburner label merge).
- Generation routing: `src/windows_gpu_preference.py`, `src/generator_launch_options.py`.
