# Releasing Digital Wellbeing

The release path is now reproducible: version bump → local/CI build → verify → tag.

## 1. Bump the release version

```powershell
python tools/bump_version.py --set 4.3.1
python tools/bump_version.py --check
```

`tools/bump_version.py` updates `version.json`, Windows resource versions,
`app.manifest`, installer/uninstaller metadata, README/download links, docs, and
the website download route/tests. Update `CHANGELOG.md` manually.

## 2. Build locally

```powershell
# Optional: only if a signing certificate is available
# $env:SIGN_PASSWORD = "..."

./installer/build_installer.ps1
```

The script:

1. builds `dist/DigitalWellbeing/` with PyInstaller;
2. signs the app if `cert.pfx` exists;
3. builds `Uninstall Digital Wellbeing.exe` and signs it;
4. stages the payload and builds `Digital Wellbeing Setup.exe`;
5. copies versioned assets:
   - `dist/DigitalWellbeingSetup-<version>.exe`
   - `dist/Uninstall Digital Wellbeing.exe`
   - `dist/DigitalWellbeing-v<version>.zip`
   - `dist/SHA256SUMS-<version>.txt`

`installer/sign_artifact.ps1` uses `signtool` + `cert.pfx` + `SIGN_PASSWORD`.
Unsigned builds are allowed for local development; release builds should always
be signed.

## 3. Verify

- File metadata reports the new version for app, setup, and uninstaller.
- Launch the built app (`--background`), setup, and uninstaller.
- Run `pytest tests -q` with `GITHUB_OWNER` / `GITHUB_REPO` set for updater tests.
- Run the website release tests (`tsx --test src/__tests__/download.test.ts`).
- Compare `SHA256SUMS-<version>.txt` with the generated files.

## 4. Tag and publish

```powershell
git add -A
git commit -m "feat: release v4.3.0 ..."
git push origin main
git tag -a v4.3.0 -m "Digital Wellbeing v4.3.0"
git push origin v4.3.0
```

The tag triggers `.github/workflows/release.yml`, which:

- validates the tag against `version.json`;
- builds app/uninstaller/installer on `windows-latest`;
- optionally signs when `WINDOWS_CERT_PFX_BASE64` / `SIGN_PASSWORD` secrets exist;
- uploads workflow artifacts;
- publishes a GitHub Release with the setup, uninstaller, zip, and checksums.

## Code signing

The workflow expects these repository secrets:

| Secret | Meaning |
|---|---|
| `WINDOWS_CERT_PFX_BASE64` | Base64 of the `.pfx` code-signing certificate |
| `SIGN_PASSWORD` | Certificate password |

Without them the release is still produced, but Windows SmartScreen will warn.
Do not commit `cert.pfx` or the password.

## Known limitations

- The custom PyInstaller setup wizard is used because Inno Setup is not required
  on the build host; it is still a single-file setup that installs the app and
  uninstaller.
- The release workflow builds on a clean Windows runner, so local `dist/`
  artifacts should not be committed.
