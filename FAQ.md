<p align="center">
  <a href="README.md">README</a> ·
  <a href="FAQ.md"><strong>FAQ</strong></a> ·
  <a href="ACKNOWLEDGEMENTS.md">Acknowledgements</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="LICENSE">License</a>
</p>

<h1 align="center">FAQ</h1>

<p align="center">
  <a href="README.md">English README</a> ·
  <a href="README.zh-CN.md">中文</a> ·
  <a href="README.ja-JP.md">日本語</a> ·
  <a href="README.ko-KR.md">한국어</a>
</p>

---

## What does this tool do?

Forza Painter FH6 turns images into Forza Horizon 6 vinyl groups. It breaks a PNG/JPG/BMP into basic shapes (rectangles, circles, ellipses, and similar primitives) that the in-game vinyl editor can display.

You pick a quality preset (or use the experimental **Tailored** preset built from Image Preview analysis), generate geometry JSON with the bundled GPU/OpenCL generator, then import that JSON into an ungrouped FH6 template.

Many people use it for anime decals, logos, and stylized artwork. High-detail generation is GPU-heavy — close other heavy apps and watch thermals during long runs. See [Hardware monitoring](docs/HARDWARE_MONITORING.md) for optional external tools.

---

## Generate JSON

1. Open **Create → Generate JSON**.
2. Click **Add images** and choose PNG/JPG/BMP files.
3. Optional: on **Image Preview**, compare preprocess filters and pick one for generation. Filter cards show **projected image complexity** (a heuristic—higher usually means more shapes—not a guaranteed final layer count).
4. Select a quality preset and optional **Preprocess Filter** (luma bands, bilateral, posterize, cel shading, etc.). Step 3 **Ready to generate** summarizes the queue, preset, and filter before you start.
5. Optional: enable **Use custom settings** to change output layers, resolution, random samples, and mutated samples.
6. Click **Start generating** and wait for the preview and logs to update.

Generated files are saved beside the source image, for example `image.500.json`, `image.1000.json`, and `image.3000.json`.

One image can produce multiple checkpoint JSON files. Prefer the highest-layer JSON that matches your template — for example, use `image.3000.json` or the final `image.json` with a 3000-layer template. Importing a 500-layer JSON into a 3000-layer template will look blurry.

| Preset | Output layers | Random samples | Use case |
| --- | ---: | ---: | --- |
| 0. Tailored (experimental, opt-in) | Per image | Per image | Built after Image Preview analyzes your image (`runtime/image-profiles/`). **Normal (slot 4) remains the recommended default.** |
| 1. Eco (Experimental) | 1500 | 90000 | Lower GPU load and temperature; softer than Slow |
| 2. Maximum Speed | 500 | 30000 | Quick composition checks |
| 3. Fast | 1000 | 60000 | Quick usable drafts |
| 4. Normal | 1800 | 120000 | Recommended default |
| 5. Slow (Conserve Shapes) | 2500 | 220000 | Final quality; 200k+ sample range |
| 6. Maximum Quality | 3000 | 350000 | Best clarity, very slow |
| 7. Maximum Power | 2900 | 1000000 | Extreme quality; your GPU will notice |

Enable **Experimental GPU cooldown between images** on the Generate tab when batching multiple images; it pauses 30 seconds between images when no GPU temperature is available in-app. Use [HWiNFO or similar](docs/HARDWARE_MONITORING.md) if you want to watch temps yourself.

---

## Text vinyl

Use **Create → Text vinyl** when in-game lettering cannot show your script (Mandarin, katakana, other CJK).

Text vinyl uses fonts installed on your PC (for example **Settings → Personalization → Fonts**). Pick an installed font or insert characters from the GB2312 library. If your text comes from an image, use **Trace from image** on the reference panel. See [`docs/TEXT_VINYL.md`](docs/TEXT_VINYL.md) for details.

---

## Import JSON

### Import Final JSON (generated geometry)

1. Start FH6 and keep **Vinyl Group Editor** open.
2. Load or create a template made from many simple sphere layers.
3. **Ungroup** the template and remember the exact in-game layer count.
4. Open **Import → Import Final JSON**, click **Refresh**, and select `forzahorizon6.exe`.
5. Enter the exact template layer count (**required**).
6. Pick a generated run folder or add `.json` files / **Use generated outputs**.
7. Click **Import final JSON into FH6** (leave advanced address fields empty unless support asks you to use them).

The app starts as a standard user. Import and export may ask for consent and, if needed, one **Administrator** prompt (UAC).

### Import Handmade JSON (type-code shapes)

1. Use the same game connection and template layer count as above.
2. Open **Import Handmade JSON**, add handmade/type-code `.json`, and review supported vs unsupported shapes in the preview.
3. Import, then **save and reload the vinyl group in FH6** so shapes display correctly.
4. Optional: trim group layer count after import; allow experimental shape codes only if you know the JSON source.

### Save from game

1. With FH6 in Vinyl Group Editor and the vinyl group you want to copy open, open **Developer Tools → Save from game**.
2. Click **Save open FH6 group** (files go to `runtime/typecode-export/` beside the app).

FH needs 4 extra boundary layers to save the cover and apply bounds correctly. Example: a 1000-layer JSON should use at least a 1004-layer template; a 3000-layer template can import about 2996 drawable shapes.

---

## Important rules

- The FH6 template must be **ungrouped** before import.
- The layer count in the app must **exactly** match the game.
- Do not switch game menus while importing.
- After restarting FH6, reloading the template, or changing layer count, import again with the new correct count.
- If JSON has fewer layers than the template, unused template layers are hidden.
- If JSON has more layers than the template, extra shapes are trimmed.
- Transparent PNG backgrounds are not imported as visible backgrounds.

---

## Downloaded source ZIP from GitHub?

**Normal users should use the `.exe` from [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases), not the automatic “Source code” ZIP.**

If you are running from source:

1. **Extract the full ZIP** (do not run batch files from inside the `.zip` preview in Explorer).
2. Double-click **`Start Forza Painter.bat`** in the extracted folder (or `start_app.bat` — same launcher).
3. First run installs Python dependencies; wait until the console finishes.
4. If no window appears, run **`Start Forza Painter (debug).bat`** — it keeps the console open and shows errors.

Windows sometimes creates a **double folder** (`forza-painter-fh6-main\forza-painter-fh6-main\`). The launcher finds the app automatically; you can run **`Start Forza Painter.bat`** from either level. See **`START_HERE.txt`** in the download.

Requirements: **64-bit Python 3.10–3.13** on PATH (or the `py` launcher).

---

## Runtime files

The one-file EXE extracts its internal files temporarily and stores normal runtime data outside the EXE. The app shows the exact paths in the startup log and on the **Tools** page.

Expected external folders beside the EXE:

- `runtime/` — logs, generated session data, and temporary app files.
- `webui-data/` — local browser/UI cache.

These folders can be deleted when the app is closed if you want to reset local runtime data. Run `clean_runtime_data.bat` in the source tree for the same cleanup during development.

---

## What are OpenCL and Vulkan?

Forza Painter’s JSON generator runs heavy image work on your **graphics card (GPU)**. To do
that, it must speak to the GPU through a standard interface. The app lets you pick which
interface — **OpenCL** or **Vulkan** — or leave **Auto** (recommended).

**OpenCL** is the default path: a long-standing cross-vendor standard for GPU computing.
It works on most NVIDIA, AMD, and Intel systems when drivers are current.

**Vulkan** is a newer graphics API (widely used in games). The generator can use the same
GPU through Vulkan instead. Some PCs run more reliably on one API than the other.

You **do not** need to install OpenCL or Vulkan separately. Update your **graphics drivers**
and keep **Backend → Auto** unless generation fails with a GPU/OpenCL/Vulkan error — then
try the other backend once.

**Backend** (OpenCL vs Vulkan) is separate from **Monitor GPU** (which physical card).
See [`docs/GPU_GENERATION.md`](docs/GPU_GENERATION.md) for the full guide.

---

## Troubleshooting

| Problem | What to try |
| --- | --- |
| EXE will not import into FH6 | Close the app and run the EXE as administrator, or accept the UAC prompt when importing. |
| GPU/OpenCL error | Update NVIDIA/AMD/Intel graphics drivers. Keep **Backend → Auto** first. If it still fails, try **Backend → Vulkan** (or OpenCL). See [What are OpenCL and Vulkan?](#what-are-opencl-and-vulkan) above. |
| Wrong GPU used for generation | Use the **Monitor GPU** dropdown in the header Resource Monitor (↻ to refresh). **Auto** is recommended. Check the log for `OpenCL: Selected device` and `GPU for generation:` lines. Integrated entries are labeled **(integrated)** and show a warning if selected. |
| OpenCL fails but Vulkan works (or vice versa) | In the Resource Monitor header, set **Backend** to **OpenCL** or **Vulkan** and retry. **Auto** leaves the generator default (OpenCL). |
| Future exact GPU binding | When a newer bundled generator adds `-list-devices` / `-gpu-id`, the app matches **Monitor GPU** automatically. See [`docs/GPU_GENERATION.md`](docs/GPU_GENERATION.md). |
| Template cannot be located | Confirm Vinyl Group Editor is open, the template is ungrouped, the layer count is exact, and you did not change menus during scanning. Import can take up to ~5 minutes. |
| Imported result is blurry | Use a higher-layer JSON or increase **Output layers** / **Random samples** (200000+ often helps). |
| Need help debugging | Use **Export detailed log** in the app and attach the log to an issue. |

---

## Will I get banned?

**Disclaimer:** You use this software at your own risk.

Forza Painter reads and writes **cosmetic vinyl editor memory** in the running FH6 process through Windows APIs (similar in spirit to memory tools like Cheat Engine). It does not modify race times, credits, car stats, or other gameplay values — but any tool that touches live game memory carries **non-zero** detection risk. Read [`docs/SAFETY.md`](docs/SAFETY.md) and [`SECURITY.md`](SECURITY.md) before importing.

Forza Horizon is a series intended for all ages. Keep it professional.

---

## Resources

- Import walkthrough video: [Bilibili](https://www.bilibili.com/video/BV1hG5Z6nENZ)
- Bundled GPU generator reference: [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu)
- Safety guide: [`docs/SAFETY.md`](docs/SAFETY.md)
- Text vinyl guide: [`docs/TEXT_VINYL.md`](docs/TEXT_VINYL.md)
- Hardware monitoring: [`docs/HARDWARE_MONITORING.md`](docs/HARDWARE_MONITORING.md)
- GPU backends (OpenCL / Vulkan): [`docs/GPU_GENERATION.md`](docs/GPU_GENERATION.md)
