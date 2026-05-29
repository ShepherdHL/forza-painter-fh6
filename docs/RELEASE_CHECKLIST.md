# Release checklist

Use this list when publishing a new `forza-painter-fh6` EXE on GitHub Releases.

## Build

- [ ] Run `scripts/publish_release.ps1` (builds EXE via PyInstaller and writes `dist/RELEASE_SNIPPET-vX.Y.Z.md` with SHA-256).
- [ ] Build from a clean tree at the tagged commit.
- [ ] Record PyInstaller (or build script) version and flags in release notes if non-standard.
- [ ] Smoke-test: launch without admin, generate JSON, import with consent + elevation, export handmade JSON.

## Security & trust

- [ ] `SECURITY.md` and `docs/SAFETY.md` match current behavior.
- [ ] Import-only elevation (no UAC on idle launch) verified.
- [ ] Helper subprocess line appears in the user log on import.

## Release artifacts

- [ ] Upload `forza-painter-fh6-vX.Y.Z.exe` (or project naming convention).
- [ ] Publish **SHA-256** hash in release notes.
- [ ] Code-sign the EXE when a certificate is available.
- [ ] Optional: VirusTotal link for the signed build.
- [ ] Copy relevant `CHANGELOG.md` section into release description.

## After publish

- [ ] If Windows Defender/smartscreen flags the build, submit a false-positive report with signed binary.
- [ ] Tag matches `app_config` / in-app version string.
