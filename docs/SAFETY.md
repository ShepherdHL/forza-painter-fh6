# Safety guide (Forza Horizon 6)

This document explains what forza-painter FH6 does to your PC and how to use it with lower risk.

## Before you import

1. **Stay in Vinyl Group Editor** — Open *Create Vinyl Group* / *Vinyl Group Editor* in FH6 and keep that screen open during import.
2. **Ungroup your template** — Grouped vinyls cause layer write failures.
3. **Know your layer count** — Enter the exact in-game template layer count in the app (required for FH6).
4. **Use generated or compatible JSON** — Higher-layer JSON on a low-layer template looks blurry.

## What happens when you click Import

1. The app shows a **consent** summary: which game process will be used and that only vinyl editor data is modified.
2. If Windows has not granted **Administrator** rights yet, the app asks to **restart elevated** (one UAC prompt). This is needed for `OpenProcess` on FH6, not for generating images offline.
3. The app may **auto-locate** the FH6 layer table (read-only scan) and validate it before writing.
4. A **helper task** runs (same application, helper mode) to perform the import. The log shows which helper started.

## What is *not* changed

The tool does not edit speed, money, cars, race results, or online stats. It only writes vinyl layer fields used by the editor.

## Account / ban risk

Reading and writing game memory while FH6 is running is similar in category to other external memory tools. Microsoft may treat this as a policy or anti-cheat risk even when changes are cosmetic.

**Use at your own risk.** The authors are not responsible for enforcement actions on your account.

## Recommended workflow

| Step | Game running? | Admin needed? |
| --- | --- | --- |
| Generate JSON (GPU) | Optional (closing FH6 reduces GPU heat) | No |
| Preview / filters | No | No |
| Import into FH6 | **Yes** (editor open) | **Yes** (when prompted) |
| Export from FH6 | **Yes** | **Yes** (when prompted) |

## Tools → FH6 diagnostics

Snapshot, compare, and table inspection tools scan game memory. **Do not use them** unless you understand memory debugging. They are not required for normal image import.

## If import fails with “access denied”

1. Accept the elevation prompt and let the app restart as Administrator.
2. Try import again.
3. Close other memory tools that may lock the FH6 process.
4. Confirm FH6 is still in Vinyl Group Editor and the process list shows the correct PID.

## Experiments folder

Scripts under `experiments/` (for example full layer blob restore) are **not** supported for daily use and may crash FH6. Stick to the main app import flow.

## More detail

See [SECURITY.md](../SECURITY.md) for technical limits and [docs/ENVIRONMENT.md](ENVIRONMENT.md) for optional environment variables.

## Translations

The app also ships `SAFETY.zh-CN.md`, `SAFETY.ja.md`, and `SAFETY.ko.md`. Open **Help → Safety guide** in the app to choose a language (shown in a built-in viewer, not an external editor).
