<p align="center">
  <img src="https://github.com/user-attachments/assets/d4f48f71-d76e-4ffe-9fb1-0b075d79bf05" alt="forza-painter FH6 logo" width="720">
</p>

<h1 align="center">forza-painter FH6</h1>

<p align="center">
  <strong>Image to Forza Horizon 6 Vinyl Group generator and importer.</strong>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">中文</a> ·
  <a href="README.ja-JP.md">日本語</a> ·
  <a href="README.ko-KR.md">한국어</a>
</p>

<p align="center">
  <code>v1.6.6</code> · <code>Windows</code> · <code>Forza Horizon 6</code> · <code>GPU/OpenCL</code> · <code>One-file EXE</code>
</p>

Convert PNG/JPG/BMP images into Forza Horizon 6 Vinyl Group layers. The app handles generation, preview, and import in one desktop window; normal users do not need Python, `.venv`, batch files, or manual memory addresses.

> **Download the EXE:** get `forza-painter-fh6-v1.6.6.exe` from [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) and run it directly.

> **If the result looks blurry:** raise `Random samples` first. Values above **200000** usually make a major quality difference; higher values are clearer but take much longer to generate.

> **Import can take time:** v1.4.1+ tries multiple FH6 template locators and can spend up to 5 minutes finding the safe layer table. Keep FH6 in Vinyl Group Editor, do not switch menus, and export a detailed log if it still fails.

| What it does | Details |
| --- | --- |
| Generate JSON | Convert images into geometry JSON with the bundled GPU/OpenCL generator. |
| Image Preview | Compare preprocess filters (luma, bilateral, posterize, cel shading, etc.) before generating. |
| Text vinyl | Type Mandarin/CJK with GB2312 picker and system fonts, or trace a reference image; see `docs/TEXT_VINYL.md`. |
| Import Final JSON | Import generated geometry JSON into FH6 (run browser + best-final picker). |
| Import Handmade JSON | Import FH6 type-code / handmade JSON (squares, circles, triangles, etc.). |
| Export Game JSON | Export the open FH6 vinyl group to handmade JSON for editing or sharing. |
| Safe FH6 workflow | Auto-locate and verify the editable layer table before writing. |
| Update check | Check for new versions on startup and show changelog notes when available. |

## Quick Start

1. Download `forza-painter-fh6-v1.6.6.exe` from [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases).
2. Put the EXE in a normal writable folder, for example `Desktop\forza-painter-fh6`.
3. Double-click the EXE. For FH6 import, run it as administrator if Windows blocks process access.
4. In FH6, open `Create Vinyl Group` / `Vinyl Group Editor`, load a sphere template, then `Ungroup` it.
5. In the app, generate JSON, open **Import Final JSON**, **enter the exact template layer count**, then import.

Do not download GitHub's automatic `Source code` ZIP unless you are developing the project. Normal users only need the `.exe`.

## Preview

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/app-import-preview.png" alt="App import page"><br>
      <strong>App import page</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-template-ready.png" alt="FH6 template ready"><br>
      <strong>Template ready in FH6</strong>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-import-result.png" alt="FH6 import result"><br>
      <strong>Imported result</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-car-applied.png" alt="FH6 car applied result"><br>
      <strong>Applied to car</strong>
    </td>
  </tr>
</table>

## Generate JSON

1. Open the `Generate JSON` page.
2. Click `Add images` and choose PNG/JPG/BMP images.
3. Optional: on **Image Preview**, compare preprocess filters and pick one for generation.
4. Select a quality preset and optional **Preprocess Filter** (luma bands, bilateral, posterize, cel shading, etc.).
5. Optional: enable `Use custom settings` to change output layers, resolution, random samples, and mutated samples.
6. Click the fixed bottom `Start generating` button.
7. Wait for the preview and logs to update.

Generated files are saved beside the source image, for example `image.500.json`, `image.1000.json`, and `image.3000.json`.

One image can generate multiple checkpoint JSON files. Prefer the highest-layer JSON that matches your template; for example, use `image.3000.json` or the final `image.json` with a 3000-layer template. Importing a 500-layer JSON into a 3000-layer template will look blurry.

| Preset | Output layers | Random samples | Use case |
| --- | ---: | ---: | --- |
| extremely fast | 500 | 30000 | Quick composition checks |
| fast | 1000 | 60000 | Quick usable drafts |
| balanced | 1800 | 120000 | Recommended default |
| slow | 2500 | 220000 | Final quality; starts using the 200k+ quality range |
| super slow | 3000 | 350000 | Best clarity, very slow |

## Text vinyl

Use the **Text vinyl** tab when in-game lettering cannot show your script (Mandarin, katakana, other CJK). 
Text Vinyl's are identified from fonts stored on your machine (ex. Settings>Personalization>Fonts). 
Pick an installed font or insert characters directly from the GB2312 library. 
If your text is derived from an image, use **Trace from image** on the reference panel (see `docs/TEXT_VINYL.md`).

## Import JSON

### Import Final JSON (generated geometry)

1. Start FH6 and keep `Vinyl Group Editor` open.
2. Load or create a template made from many simple sphere layers.
3. `Ungroup` the template and remember the exact in-game layer count.
4. Open **Import Final JSON**, click `Refresh`, and select `forzahorizon6.exe`.
5. Enter the exact template layer count (**required**).
6. Pick a generated run folder or add `.json` files / **Use generated outputs**.
7. Click **Import final JSON into FH6** (leave advanced address fields empty unless support asks you to use them).

### Import Handmade JSON (type-code shapes)

1. Use the same game connection and template layer count as above.
2. Open **Import Handmade JSON**, add handmade/type-code `.json`, and review supported vs unsupported shapes in the preview.
3. Import, then **save and reload the vinyl group in FH6** so shapes display correctly.
4. Optional: trim group layer count after import; allow experimental shape codes only if you know the JSON source.

### Export Game JSON

1. With FH6 in Vinyl Group Editor and the vinyl group you want to copy open, open **Export Game JSON**.
2. Click **Export open FH6 group to JSON** (files go to `runtime/typecode-export/` beside the app).

FH needs 4 extra boundary layers to save the cover and apply bounds correctly. Example: a 1000-layer JSON should use at least a 1004-layer template; a 3000-layer template can import about 2996 drawable shapes.

## Important Rules

- The FH6 template must be ungrouped before import.
- The layer count in the app must exactly match the game.
- Do not switch game menus while importing.
- After restarting FH6, reloading the template, or changing layer count, import again with the new correct count.
- If JSON has fewer layers than the template, unused template layers are hidden.
- If JSON has more layers than the template, extra shapes are trimmed.
- Transparent PNG backgrounds are not imported as visible backgrounds.

## Runtime Files

The one-file EXE extracts its internal files temporarily and stores normal runtime data outside the EXE. The app shows the exact paths in the startup log and on the `Tools` page.

Expected external folders beside the EXE:

- `runtime/`: logs, generated session data, and temporary app files.
- `webui-data/`: local browser/UI cache.

These folders can be deleted when the app is closed if you want to reset local runtime data.

## Troubleshooting

- **EXE will not import into FH6:** close the app and run the EXE as administrator.
- **GPU/OpenCL error:** update NVIDIA/AMD/Intel graphics drivers. The bundled generator uses OpenCL.
- **Template cannot be located:** confirm you are in Vinyl Group Editor, the template is ungrouped, the layer count is exact, and the menu was not changed during scanning.
- **Imported result is blurry:** use a higher-layer JSON or increase `Output layers` / `Random samples`.
- **Need help debugging:** use `Export detailed log` in the app and attach the log to an issue.

## Resources

- Import walkthrough video: `https://www.bilibili.com/video/BV1hG5Z6nENZ`
- Bundled GPU generator source/reference: `https://github.com/zjl88858/forza-painter-geometrize-gpu`
- Full changelog: [CHANGELOG.md](CHANGELOG.md)

## FAQ

*(Adapted from the_adawg's)*

### What exactly does this tool do?

If you've ever seen any iteration of [TRON](https://youtu.be/6Nn7J1Eb87E?si=m6VR8BdN_jAZZMgo), it's a lot like that, but now you get to watch it happen to an image in real time. For most users, that seems to be every anime or cartoon character ever created.

This program takes any image and breaks it apart into primitive shapes used in the Forza Horizon vinyl editor: squares, rectangles, circles, or (ideally) whichever shapes work best for the image you're importing.

You can choose the level of detail from six presets, or write your own. Each preset ranges from low detail / fast processing to high detail / long processing.

This version uses your graphics card (GPU) to process the image into shapes. If you're generating high detail, it's recommended to close the game during generation so you don't overheat your machine. A warning system is integrated as well—check the output log every so often during generation. Unless your machine is over a decade old, you'll hopefully never see a warning.

### Will this get me banned?

**Disclaimer:** I take no responsibility for your use of this software.

You may be reported by players if you share vinyls that are extremely detailed. Some players feel that making vinyl groups this way is unfair because they learned the tool without an easy starting point.

*(Note: Many players will not report you. Hand-made vinyls typically use far fewer layers and are more efficient—they may simply outclass automated designs instead.)*

That opinion is valid, and with enough time, practice, and talent you can recreate very complex images by hand. I simply don't share the view that you should have to.

Forza Painter reads and writes directly to Forza Horizon 6's memory using Windows system APIs—the same low-level approach used by tools like Cheat Engine. It only modifies cosmetic vinyl/livery editor data. It does not change player speed, position, credits, car vouchers, race time, stats, or similar gameplay values.

Because it accesses game memory while the game is running, there is a non-zero risk that anti-cheat or account systems could flag it. **Use this tool at your own risk.**

### Will this get me in trouble?

That depends on what you upload with this tool. Generally, if you follow the game's Terms of Service, you should be fine. The important rules are about the content you create, not necessarily the tool itself.

Forza Horizon is intended for all ages. Keep it professional.

## Acknowledgements

This project is a derivative of the Forza Painter workflow and retains upstream MIT license notices.

| Person / project | Link | Contribution |
| --- | --- | --- |
| the_adawg (AE) | [forza-painter/forza-painter](https://github.com/forza-painter/forza-painter) | Original Forza Painter project: MIT-licensed FH import workflow, memory-writing/import foundation, and geometry-to-vinyl approach. |
| Sam Twidale | [samcodes.co.uk](https://samcodes.co.uk/) | geometrize-lib; original geometry approximation work credited by upstream licenses. |
| Michael Fogleman | [fogleman/primitive](https://github.com/fogleman/primitive) | Primitive library; original primitive-based image approximation credited by upstream licenses. |
| Omar Cornut | [ocornut/imgui](https://github.com/ocornut/imgui) | Dear ImGui; GUI framework used by the original forza-painter. |
| DxBang | [Bang's Forza Color Converter](https://bang.systems/forza-colors/) | Forza H/S/B color conversion used in Tools → Color Picker. |
| bvzrays | [bvzrays/forza-painter-fh6](https://github.com/bvzrays/forza-painter-fh6) | FH6-focused desktop fork: UI, importer/locator behavior, app packaging, and workflow ideas for Forza Horizon 6. |
| Kloudy (heyitshestia) | [kloudys-fh6-painter](https://github.com/heyitshestia/kloudys-fh6-painter) | FH6 painter fork: launcher workflow, style presets, Luma Prep, Edge Repair, finalized-run browser, updater flow, release packaging, and handmade/universal importer work. |
| zjl88858 | [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu) | GPU/OpenCL geometrize generator lineage used by the bundled generator workflow. |
| LibreHardwareMonitor | [LibreHardwareMonitor/LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | Hardware monitoring backend for the header resource telemetry panel. |
| H3XDaemon | [H3XDaemon](https://github.com/H3XDaemon) | Contributor to this repository. |
| MaccLochlainn | [MaccLochlainn](https://github.com/MaccLochlainn) | Contributor to this repository. |
| ree9622 | [ree9622](https://github.com/ree9622) | Korean localization contributor in upstream history. |

See the full [contributor graph](https://github.com/ShepherdHL/forza-painter-fh6/graphs/contributors) for all commits to this repository.

## Changelog

Only versioned release entries are kept here. See [CHANGELOG.md](CHANGELOG.md) for the app update prompt changelog.

### v1.6.6 / 2026-05-26

- Updated the app version to `v1.6.6`; release packages now use `forza-painter-fh6-v1.6.6.exe`.
- Fixed `luma_band` preprocessing for RGB/BGR handling and made preprocessed-image writes atomic.
- Packaged OpenCV and NumPy into the one-file EXE so `luma_band` preprocessing works in release builds.
- Import now requires the FH6 template layer count before starting.
- Refactored core modules with typed exceptions and shared utility helpers.

### v1.6.5 / 2026-05-25

- Updated the app version to `v1.6.5`; release packages now use `forza-painter-fh6-v1.6.5.exe`.
- Updated the bundled GPU generator to upstream `v1.2-Canary-20260525`.
- Bundled presets now set `forceOpaqueShapes = false` by default.
- Reduced main-app overhead during generation by using a sanitized generator environment and slower file polling.

### v1.6.1 / 2026-05-24

- Updated the app version to `v1.6.1`; release packages now use `forza-painter-fh6-v1.6.1.exe`.
- Disabled `luma_band` preprocessing by default in bundled presets.
- Import no longer reuses stale FH6 session data from `webui-data`; it re-locates the current template before writing.
- JSON previews now use one stable renderer path to avoid ellipse preview distortion differences between packaged EXE environments.

### v1.6.0 / 2026-05-24

- Updated the app version to `v1.6.0`; release packages now use `forza-painter-fh6-v1.6.0.exe`.
- Updated the bundled GPU generator to upstream `canary-26052401`.
- Added upstream `errorGridSize` preset support.
- Integrated the upstream transparent-area overhang prevention algorithm adjustment.
- Significantly improved generation quality for the large ellipse at the bottom of transparent images.

### v1.5.4 / 2026-05-23

- Fixed preview scaling for high-resolution source images, generator preview PNGs, and JSON previews so the full image fits the current preview panel without stretching.
- Fixed type 16 rotated ellipse rendering in JSON previews so Import page previews no longer flatten or rotate ellipse strokes incorrectly.

### v1.5.3 / 2026-05-22

- Added EXE-friendly custom preset import, image/JSON list removal, checkpoint reuse, safer output naming, and Pillow preview fallback.

### v1.5.2 / 2026-05-22

- Added a true one-file EXE so normal users no longer need Python, `.venv`, or helper files.
- The GUI EXE can relaunch itself in hidden helper mode for import and FH6 memory probing.
- The Tools page and startup log now show external runtime/cache locations.

### v1.5.1 / 2026-05-22

- Fixed startup dependency installation when a project `.venv` exists but its Python does not have `pip`.
- Improved startup-script diagnostics for incomplete source-package extraction.

### v1.5.0 / 2026-05-22

- Updated the bundled GPU/OpenCL generator to upstream `canary-26052102`.
- Added the upstream work-group evaluation algorithm from PR #4 for faster GPU candidate evaluation.
- Added startup update checking, root `CHANGELOG.md`, and the dark desktop UI.

### v1.4.1 / 2026-05-21

- FH6 template auto-location now tries both v1.3 and v1.4 scan strategies before giving up.
- Added an RTTI vtable fallback locator and increased the auto-location wait budget.

### v1.4.0 / 2026-05-21

- Added detailed log export capped at 50000 characters.
- Improved FH6 template auto-location for large writable memory regions.

### v1.3.0 / 2026-05-21

- Updated the bundled GPU/OpenCL generator to upstream `canary-26052101`.
- Added the upstream GPU device-selection fix and selected-device logging.

### v1.2.0 / 2026-05-20

- Updated the bundled GPU/OpenCL generator to upstream `canary-26052001`.
- Added `forceOpaqueShapes = true` to bundled and custom generation settings.

### v1.1.1 / 2026-05-20

- Added centralized version management for the app window, CLI, and release package names.
- Reorganized the repository layout and release packaging.
