# Text vinyl (Mandarin / CJK)

**Walkthrough with screenshots:** [TEXT_VINYL_GUIDE.md](TEXT_VINYL_GUIDE.md)

Forza's in-game text tool cannot render most non-Latin scripts. This mode builds vinyl
layers from traced glyph masks using **real FH6 vinyl shapes** (squares, circles,
ellipses, triangles, or mixed) so readable Mandarin, katakana,
hiragana, **Korean (Hangul)**, and other CJK scripts can be imported.

**Korean:** Use the Hangul syllable picker or type/paste directly. Choose a font tagged
**[KR]** in the dropdown, such as **Malgun Gothic** (`malgun`).

## In the app

Open the **Text vinyl** tab (a dedicated workspace: settings and script tabs on the left,
reference image + JSON previews on the right). Generated designs stay on this tab until you
click **Continue to Import → Text**, which opens **Import → Import text** with your design selected.

Use the script sub-tabs:

| Tab | Use for | Font list |
|-----|---------|-----------|
| **Universal (Latin)** | English, numbers, Western punctuation | [LATIN] fonts; **Latin extended** character grid |
| **Japanese** | Hiragana, katakana, kanji | [JP] / [CJK] fonts; sub-tabs **Hiragana**, **Katakana**, **Kanji (JIS)** grids |
| **Kaomoji** | Japanese emoticon faces | Monospace / [SYMBOL] fonts; **Kaomoji library** (click to insert) |
| **Korean** | Hangul | [KR] fonts; **Hangul syllables** grid (paginated) |
| **Chinese** | Simplified/traditional hanzi | [SC] / [TC] / [CJK] fonts; **GB2312 hanzi** grid |

Each tab keeps its own text, font choice, and **Search fonts** filter. Below the text field, use the **character grid** (click a cell to insert; search and page through large sets). Scroll down for **Generation options** (preset, size, shape mode, color).

**Quality presets** (Generation options):

| Preset | Use for |
|--------|---------|
| **Custom** | Your manual trace cell size and shape mode |
| **Efficient CJK** | Fewer layers (larger cell grid); optional **Fit to layer budget** |
| **Sharp CJK** | Mixed squares/triangles, cell size 2 |
| **Soft CJK** | Ellipse trace, cell size 3 |
| **In-game Forza font (Latin)** | One FH6 glyph layer per character (Universal tab only); enable **Use in-game Forza fonts** |
| **Smooth CJK (extra shapes)** | Quarter circle corners + rounded squares (`cell` 2); enable **Enable extra shapes** |

**Enable extra shapes (smoother curves)** uses FH6 **Quarter Circle**, **Rounded Square**, **Circle**, **Ellipse**, and **Square** primitives at convex corners and along strokes. Best for Japanese/katakana; uses more shape types than basic trace modes. Incompatible with **Use in-game Forza fonts** (those are Latin-only).

A **layer estimate** updates as you type (drawable layers + ~4 template boundary layers). Any PC font can be used for trace mode—**Browse font file** if it does not appear in the list.

### Typed text (cleanest workflow)

1. Open the tab for your script and enter text (examples: `SONIC`, `ソニック`, `안녕`, `你好世界`).
2. Use **Search fonts** to filter the dropdown, or **Browse font file** for any `.ttf` / `.ttc` / `.otf`.
3. Click characters in the script’s **character grid** to insert symbols (or type/paste directly).
4. Check the coverage line under the options — it reports missing glyphs for the selected font.
5. Set **Trace shape mode** (see table below) and match your FH6 template before import.
6. Adjust **font size** and **trace cell size** (default **1** = sharpest detail; larger → fewer layers, blockier shapes).
7. Click **Generate from text**.
8. Preview the design on the right, then click **Continue to Import → Text** when ready.
9. On **Import → Import text**, confirm your design and import as usual.

Default font priority favors Simplified Chinese faces (Microsoft YaHei, SimHei, Noto Sans SC), then Traditional Chinese, Japanese, and Korean fonts.

### Trace shape modes

| Mode | FH6 vinyl shape | Best for | Import |
|------|-----------------|----------|--------|
| **rectangles** | Square | Fewest layers, blocky but clear CJK | **Import → Import text** (type-code JSON) |
| **squares** | Square | Chunky pixel / retro look | Import text |
| **ellipses** | Ellipse | Softer strokes, more layers | Import text |
| **circles** | Circle | Rounded katakana dots and curves | Import text |
| **triangles** | Triangle | Sharper angular strokes | Import text |
| **mixed** | Square on long bars, triangle elsewhere | Katakana with horizontal + corner strokes | Import text |

Generated designs use **FH6 type-code JSON** (`fh6_text_typecode_v1`). Import them on **Import → Import Text Vinyl**, not Import .JSON. After import, **save and reload the vinyl group in FH6** so shapes display correctly. Legacy geometry JSON (types 1 / 16) from older builds is still imported via the geometry path if you open those files.

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
