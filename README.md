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
  <a href="README.md"><strong>README</strong></a> ·
  <a href="FAQ.md">FAQ</a> ·
  <a href="ACKNOWLEDGEMENTS.md">Acknowledgements</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="LICENSE">License</a>
</p>

<p align="center">
  <code>v1.6.6</code> · <code>Windows</code> · <code>Forza Horizon 6</code> · <code>GPU/OpenCL</code> · <code>One-file EXE</code>
</p>

Convert PNG/JPG/BMP images into Forza Horizon 6 Vinyl Group layers. The app handles generation, preview, and import in one desktop window; normal users do not need Python, `.venv`, batch files, or manual memory addresses.

> **Download the EXE:** get `forza-painter-fh6-v1.6.6.exe` from [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) and run it directly.

> **If the result looks blurry:** raise **Random samples** first. Values above **200000** usually make a major quality difference; higher values are clearer but take much longer to generate.

> **Import can take time:** the app tries multiple FH6 template locators and can spend up to 5 minutes finding the safe layer table. Keep FH6 in Vinyl Group Editor, do not switch menus, and export a detailed log if it still fails.

| What it does | Details |
| --- | --- |
| Generate JSON | Convert images into geometry JSON with the bundled GPU/OpenCL generator. |
| Image Preview | Compare preprocess filters (luma, bilateral, posterize, cel shading, etc.) before generating. |
| Text vinyl | Type Mandarin/CJK with GB2312 picker and system fonts, or trace a reference image. |
| Import photo | Import designs generated from photos into FH6. |
| Import text | Import text vinyl designs into FH6. |
| Import pixel art | Import pixel art with FH6 shape layers into FH6. |
| Save from game | Save the open FH6 vinyl group as a design file. |
| Safe FH6 workflow | Auto-locate and verify the editable layer table before writing. |
| Update check | Check for new versions on startup and show changelog notes when available. |

## Quick Start

1. Download `forza-painter-fh6-v1.6.6.exe` from [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases).
2. Put the EXE in a normal writable folder, for example `Desktop\forza-painter-fh6`.
3. Double-click the EXE. The app starts as a standard user; when you **import or export** into FH6 it will ask for consent and, if needed, one **Administrator** prompt (UAC).
4. In FH6, open `Create Vinyl Group` / `Vinyl Group Editor`, load a sphere template, then `Ungroup` it.
5. In the app, use **Create** to generate a design, then **Import → Import photo**, **Import text**, or **Import pixel art** (matching what you made). **Enter the exact template layer count**, then import. Use **Help** in the header for the tutorial and safety guide.

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

## Quality presets (summary)

| Preset | Layers | Random samples | Notes |
| --- | ---: | ---: | --- |
| 0. Tailored (experimental) | Per image | Per image | Opt-in; built from Image Preview. **Normal (4) is the default.** |
| 1. Eco (Experimental) | 1500 | 90000 | Lower GPU load |
| 4. Normal | 1800 | 120000 | Recommended default |
| 7. Maximum Power | 2900 | 1000000 | Highest quality, slowest |

Full preset table, generate/import walkthroughs, troubleshooting, and safety notes: **[FAQ.md](FAQ.md)** · [Wiki → FAQ](https://github.com/ShepherdHL/forza-painter-fh6/wiki/FAQ)

## More documentation

| Document | Contents |
| --- | --- |
| [Wiki](https://github.com/ShepherdHL/forza-painter-fh6/wiki) | Official GitHub Wiki mirror (FAQ, Acknowledgements, Changelog) |
| [FAQ.md](FAQ.md) | Workflows, rules, troubleshooting, ban/safety FAQ |
| [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) | Credits and upstream lineage |
| [CHANGELOG.md](CHANGELOG.md) | Version history (also used by the in-app updater) |
| [SECURITY.md](SECURITY.md) | Security policy |
| [.github/SUPPORT.md](.github/SUPPORT.md) | GitHub support / help entry point |
| [docs/SAFETY.md](docs/SAFETY.md) | Memory access and trust guide |
| [docs/TEXT_VINYL.md](docs/TEXT_VINYL.md) | Text vinyl reference |
| [docs/HARDWARE_MONITORING.md](docs/HARDWARE_MONITORING.md) | Optional external GPU/CPU monitoring |

Maintainers: run `scripts/publish_wiki.ps1` after editing root docs to refresh the Wiki tab.
