# Text vinyl (Mandarin / CJK)

Forza's in-game text tool cannot render most non-Latin scripts. This mode builds vinyl
layers from traced glyph masks using **selectable primitives** (rectangles, squares,
ellipses, circles, triangle-style diamonds, or mixed) so readable Mandarin, katakana,
hiragana, **Korean (Hangul)**, and other CJK scripts can be imported.

**Korean:** Type or paste Hangul directly (the hanzi library is GB2312 only). Choose a
font tagged **[KR]** in the dropdown, such as **Malgun Gothic** (`malgun`). Simplified-Chinese-only
fonts like SimSun may list as [SC] but will not draw Korean reliably.

## In the app

Open the **Text vinyl** tab (a dedicated workspace: settings and script tabs on the left,
reference image + JSON previews on the right). Generated JSON stays on this tab until you
click **Add to Import Final**, then continue in the **Import Final JSON** tab as usual.

Use the script sub-tabs:

| Tab | Use for | Font list |
|-----|---------|-----------|
| **Universal (Latin)** | English, numbers, Western punctuation | [LATIN] fonts (Segoe UI, Arial, …) |
| **Japanese** | Hiragana, katakana, kanji | [JP] / [CJK] fonts |
| **Korean** | Hangul | [KR] fonts |
| **Chinese** | Simplified/traditional hanzi + GB2312 picker | [SC] / [TC] / [CJK] fonts |

Each tab keeps its own text, font choice, and **Search fonts** filter. Shared options (size, shape mode, color) apply to whichever tab is active.

### Typed text (cleanest workflow)

1. Open the tab for your script and enter text (examples: `SONIC`, `ソニック`, `안녕`, `你好世界`).
2. Use **Search fonts** to filter the dropdown, or **Browse font file** for any `.ttf` / `.ttc` / `.otf`.
3. Use the **Mandarin character library** to search and insert GB2312 Level-1 hanzi (3755 characters).
4. Check the coverage line under the options — it reports missing glyphs for the selected font.
5. Set **Trace shape mode** (see table below) and match your FH6 template before import.
6. Adjust **font size** and **trace cell size** (larger cell → fewer layers, less detail).
7. Click **Generate from text**.
8. Preview the JSON on the right, then click **Add to Import Final** when ready.
9. Open **Import Final JSON** and import as usual.

Default font priority favors Simplified Chinese faces (Microsoft YaHei, SimHei, Noto Sans SC), then Traditional Chinese, Japanese, and Korean fonts.

### Trace shape modes

| Mode | JSON primitive | Best for | FH6 template |
|------|----------------|----------|--------------|
| **rectangles** | Axis-aligned rectangles | Fewest layers, blocky but clear CJK | Ungrouped **rectangle** layers (or spheres) |
| **squares** | Equal-width/height rectangles | Chunky pixel / retro look | Rectangle template |
| **ellipses** | Rotated ellipses (type 16) | Softer strokes, more layers | Ungrouped **sphere** template |
| **circles** | Round ellipses per region | Rounded katakana dots and curves | Sphere template |
| **triangles** | Thin or diamond ellipses | Sharper angular strokes (approximation) | Sphere template |
| **mixed** | Rectangles on long bars, diamonds elsewhere | Katakana with horizontal + corner strokes | Sphere template |

FH6 import only supports **rectangles** and **rotated ellipses** in geometry JSON. True in-game triangle vinyl shapes are not wired up yet; **triangles** mode uses angled ellipses to suggest corners.

### Stylized text from an image (preserves custom lettering)

1. Export a high-contrast PNG of your word (transparent or solid background).
2. **Browse** to that image.
3. Choose the same **trace shape mode** you plan to use in-game.
4. Enable **Invert** if the letters are light on a dark background.
5. Click **Trace from image**.

This traces the pixels you see—not the in-game font—so complex custom logos work.

## Command line

```bat
cd src
python text_to_json.py --list-fonts
python text_to_json.py --text "你好" --font "Microsoft YaHei [SC]" --output ..\runtime\text-vinyl\sample.json
python text_to_json.py --text "カタカナ" --shape-mode ellipses --output ..\runtime\text-vinyl\katakana.json
python text_to_json.py --text "ソニック" --shape-mode mixed --cell-size 3 --output ..\runtime\text-vinyl\sonic.json
python text_to_json.py --image word.png --shape-mode rectangles --output ..\runtime\text-vinyl\traced.json --cell-size 3
```

`--shape-mode` choices: `rectangles`, `squares`, `ellipses`, `circles`, `triangles`, `mixed`.

## Tips

| Goal | Suggestion |
|------|------------|
| Fewest layers | **rectangles**, cell size 5–8 |
| Sharper edges | cell size 2–3, accept more layers |
| Softer Japanese curves | **ellipses** or **circles**, sphere template |
| Angular katakana | **triangles** or **mixed**, sphere template |
| Custom font look | Trace from image |
| Rare hanzi missing | Browse a fuller font (Noto Sans SC CJK, Source Han Sans SC) |
| Korean (Hangul) | Pick a **[KR]** font (Malgun Gothic); avoid SC-only faces like SimSun |
| Template size | FH needs JSON drawable layers + 4 boundary layers |
