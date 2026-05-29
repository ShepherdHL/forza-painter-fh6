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
3. Optional: on **Image Preview**, compare preprocess filters and pick one for generation.
4. Select a quality preset and optional **Preprocess Filter** (luma bands, bilateral, posterize, cel shading, etc.).
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

### Export Game JSON

1. With FH6 in Vinyl Group Editor and the vinyl group you want to copy open, open **Export Game JSON**.
2. Click **Export open FH6 group to JSON** (files go to `runtime/typecode-export/` beside the app).

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

## Runtime files

The one-file EXE extracts its internal files temporarily and stores normal runtime data outside the EXE. The app shows the exact paths in the startup log and on the **Tools** page.

Expected external folders beside the EXE:

- `runtime/` — logs, generated session data, and temporary app files.
- `webui-data/` — local browser/UI cache.

These folders can be deleted when the app is closed if you want to reset local runtime data. Run `clean_runtime_data.bat` in the source tree for the same cleanup during development.

---

## Troubleshooting

| Problem | What to try |
| --- | --- |
| EXE will not import into FH6 | Close the app and run the EXE as administrator, or accept the UAC prompt when importing. |
| GPU/OpenCL error | Update NVIDIA/AMD/Intel graphics drivers. The bundled generator uses OpenCL. |
| Template cannot be located | Confirm Vinyl Group Editor is open, the template is ungrouped, the layer count is exact, and you did not change menus during scanning. Import can take up to ~5 minutes. |
| Imported result is blurry | Use a higher-layer JSON or increase **Output layers** / **Random samples** (200000+ often helps). |
| Need help debugging | Use **Export detailed log** in the app and attach the log to an issue. |

---

## Will I get banned?

**Disclaimer:** You use this software at your own risk.

Forza Painter reads and writes **cosmetic vinyl editor memory** in the running FH6 process through Windows APIs (similar in spirit to memory tools like Cheat Engine). It does not modify race times, credits, car stats, or other gameplay values — but any tool that touches live game memory carries **non-zero** detection risk. Read [`docs/SAFETY.md`](docs/SAFETY.md) and [`SECURITY.md`](SECURITY.md) before importing.

Sharing extremely detailed vinyls may draw reports from other players. That is a community norms question as much as a technical one. Complex art is possible by hand with enough time; this tool is for people who prefer not to spend that time on every design.

Keep uploads appropriate for an all-ages game.

---

## Resources

- Import walkthrough video: [Bilibili](https://www.bilibili.com/video/BV1hG5Z6nENZ)
- Bundled GPU generator reference: [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu)
- Safety guide: [`docs/SAFETY.md`](docs/SAFETY.md)
- Text vinyl guide: [`docs/TEXT_VINYL.md`](docs/TEXT_VINYL.md)
- Hardware monitoring (external tools): [`docs/HARDWARE_MONITORING.md`](docs/HARDWARE_MONITORING.md)
