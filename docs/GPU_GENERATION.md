# GPU generation routing

How Forza Painter chooses which graphics adapter runs JSON generation.

## What are OpenCL and Vulkan?

**Short answer:** they are two different “languages” your generator can use to run work on
your **graphics card (GPU)**. You do **not** need to understand them to use Forza Painter.
Leave **Backend → Auto** unless something goes wrong.

### Why does the generator mention them?

Turning a photo into vinyl JSON is heavy math. The bundled generator offloads that work to
your GPU so generation finishes in minutes instead of hours. To reach the GPU, the program
must use a **graphics API** — a standard way for software to ask the driver for compute
work. Forza Painter’s generator supports two APIs:

| Name | In plain terms | When to use |
| --- | --- | --- |
| **OpenCL** | An older, widely supported standard for “general” GPU computing. Works on most NVIDIA, AMD, and Intel GPUs with up-to-date drivers. | **Default.** This is what **Auto** uses. |
| **Vulkan** | A newer graphics API (common in modern games). The generator can use the same GPU through Vulkan instead of OpenCL. | Try this **only if OpenCL errors** or crashes and your drivers are already updated. |

**OpenCL and Vulkan are not brand names for your card.** They do not replace **Monitor GPU**
(which physical card to use). They only change *how* the generator talks to whatever card
Windows and your selection already pointed it at.

### What should I pick in the app?

| Backend setting | Meaning |
| --- | --- |
| **Auto (recommended)** | Generator default — OpenCL. Best choice for almost all users. |
| **OpenCL** | Force OpenCL explicitly (same as Auto for current builds). |
| **Vulkan** | Force Vulkan. Use for troubleshooting if OpenCL fails. |

If generation works on **Auto**, do not change Backend.

### Common misconceptions

- **“Do I need to install OpenCL or Vulkan?”** — No separate install for normal use.
  Keep **graphics drivers** updated (NVIDIA GeForce Experience, AMD Adrenalin, Intel Arc).
- **“Is Vulkan better because it’s newer?”** — Not always. Speed and stability depend on
  your GPU and drivers. Auto/OpenCL is the supported default.
- **“Is this related to FH6 graphics settings?”** — No. This only affects JSON **generation**
  inside Forza Painter, not in-game FH6 rendering.

---

## User controls (header Resource Monitor)

| Control | Purpose |
| --- | --- |
| **Monitor GPU** | Select adapter for telemetry, eco cooldown, and generation steering. **Auto (recommended)** leaves choice to Windows + generator defaults. |
| **Backend** | **Auto** (generator default, OpenCL), **OpenCL**, or **Vulkan**. Passed as `-backend` when not Auto. Changing Backend writes a short explanation to the **output log**. |
| **↻** | Re-enumerate adapters (WMI + MSI Afterburner labels). |

Settings are saved to `runtime/settings/generator_gpu.json`:

```json
{
  "gpu_selection_id": "auto",
  "generator_backend": "auto"
}
```

Integrated adapters appear as **(integrated)**. Selecting one shows a confirmation
dialog because iGPU generation is slower, less stable, and runs hotter.

## Routing priority at generate time

```
1. Direct OpenCL/Vulkan binding (-gpu-id N)     [when bundled exe supports it]
2. Windows UserGpuPreferences (per-exe registry) [when a specific GPU is selected]
3. Generator default device selection           [Auto]
```

Optional **`-backend opencl|vulkan`** is appended whenever Backend is not Auto and
the bundled exe declares `-backend` in its usage text.

### Phase 2 (current bundled canary)

The bundled `forza-painter-geometrize-go.exe` supports **`-backend`** only.
When you pick a specific GPU, the app sets Windows **DirectX UserGpuPreferences**
for the generator executable:

- Discrete → high performance
- Integrated → power saving
- Auto → preference entry removed

Check the log for:

- `GPU for generation: …` (registry routing)
- `Generator backend: …` (when Backend ≠ Auto)
- `OpenCL: Selected device …` (ground truth from generator stdout)

### Phase 3 (future bundled canary)

When upstream adds **`-list-devices`** and **`-gpu-id`**, the app will:

1. Probe capabilities at startup (`direct GPU binding=yes` in log)
2. Run `-list-devices` and cache the device list
3. Match **Monitor GPU** WMI name to an OpenCL/Vulkan device index
4. Pass `-gpu-id N` on generate (registry routing skipped for that run)

No Forza Painter app update is required beyond replacing the bundled exe—capability
probe is automatic.

## Upstream generator contract (for maintainers)

Target repo: [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu)

Suggested CLI additions:

```
-list-devices
    Print available devices for the selected backend and exit 0.
    stdout: JSON (preferred) or indexed text lines.

-gpu-id int
    Bind generation to device index from -list-devices for this run.
```

### JSON format (preferred)

```json
{
  "backend": "opencl",
  "devices": [
    {
      "index": 0,
      "name": "AMD Radeon Graphics",
      "vendor": "Advanced Micro Devices, Inc.",
      "type": "integrated"
    },
    {
      "index": 1,
      "name": "NVIDIA GeForce RTX 4070",
      "vendor": "NVIDIA Corporation",
      "type": "discrete"
    }
  ]
}
```

### Text fallback (also supported by the app)

```
0: NVIDIA GeForce RTX 4070
1: AMD Radeon Graphics
```

### Example generate command (future)

```cmd
forza-painter-geometrize-go.exe image.png ^
  -settings preset.ini ^
  -output out ^
  -preview preview.png ^
  -backend opencl ^
  -gpu-id 1
```

## Vulkan release packaging

Upstream release bundles include `vulkan-1.dll` and SPIR-V shaders. If **Backend →
Vulkan** fails on end-user machines, verify those files ship beside the generator
exe in your release layout (OpenCL remains the default).

## Troubleshooting

See [FAQ.md](../FAQ.md) — rows for wrong GPU, OpenCL vs Vulkan, and future exact binding.

## Code map

| Module | Role |
| --- | --- |
| `src/gpu_adapters.py` | WMI enumeration, integrated detection, Afterburner index merge |
| `src/generator_gpu_settings.py` | Persist selection + backend |
| `src/generator_capabilities.py` | Probe exe flags from usage text |
| `src/generator_devices.py` | Parse `-list-devices`, match adapter names |
| `src/generator_launch_options.py` | Build `-backend` / `-gpu-id` argv |
| `src/windows_gpu_preference.py` | DirectX UserGpuPreferences registry |
| `src/ui/header_telemetry.py` | Monitor GPU + Backend UI |

Tests: `tests/test_gpu_adapters.py`, `tests/test_generator_capabilities.py`,
`tests/test_generator_backend_gpu.py`, `tests/test_windows_gpu_preference.py`.
