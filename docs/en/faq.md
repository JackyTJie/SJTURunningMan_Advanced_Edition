# FAQ and Troubleshooting

## General

### Uploads fail — what now

This version tolerates off-campus login. If it still fails, work through these in order:

1. **Clear app data** — phone: **Settings → Apps → this app → Storage → Clear data + Clear cache**, then reopen and log in again.
2. **Check the cookie** — cookies expire within hours to days; log in again to refresh. When pasting manually, make sure nothing is missing.
3. **Check the network** — try WiFi vs mobile data, confirm the campus network is not blocking you.
4. **Wait** — the 交我办 servers may be down for maintenance; retry later.

### What should I set for a first run

**Count 1**, distance 2 km or more — verify the account and flow work before scaling up.

### Why avoid 1 km

The point-filling algorithm struggles to hit very short distances and may fall under 1 km. Use **2 km or more**.

### Multiple devices

Logging in the same account on several devices at once can invalidate the cookie. Don't keep several sessions alive simultaneously.

### Cookie safety

A cookie is a credential. **Never share it**, and never paste it into issues, logs or screenshots. See [SECURITY.md](../../SECURITY.md).

---

## Desktop

### SmartScreen / Gatekeeper blocks launch

For Windows, review the source and use More info → Run anyway if appropriate. For macOS installation, see [macos.md](macos.md).

### Route preview does not open

The in-app preview works offline. The map button embeds an OpenStreetMap map from a loopback-only HTTP page inside the preview card, allowing OSM's required Referer, and no longer opens the system browser or shows an engine switch/status bar. If tiles fail to load, check access to Leaflet/OSM; the card reports failures while retaining the track, and reopening the map after restarting the client is enough. If an old map still shows “403 / Access blocked”, make sure it is not the old `file://` page; see [desktop.md](desktop.md).

### Missing executable icon

Build the native executable with `build_windows.ps1` (it builds the React frontend first); `desktop/src-tauri/build.rs` and the Tauri bundle config embed the icon and version. The repository no longer ships a PyInstaller spec, so the legacy packaging command cannot build the Tauri client either.

### Imported routes disappeared after restarting

Copies live in the OS user data directory’s `routes/`, independently of the installation directory. Check the active OS account and any reported data-directory errors. Legacy Routes/user.txt must be imported manually.

### Import does nothing or rejects the file

On the Routes page, use Import TXT and select UTF-8 text with one BD09 longitude,latitude pair per line. Limits are 2 MB and 30,000 distinct consecutive points. Cancellation makes no changes. See [routes.md](routes.md).

### How is the graphical CAPTCHA handled?

The desktop client prefills the editable CAPTCHA field using the legacy recognition service. You can correct the result directly, refresh to retry, or fill in the same field manually if recognition fails. Login preserves the legacy delay after recognition and follows the server's returned redirect. Account login and My SJTU app verification have been checked live. When the school requires a six-digit second-factor code, the account holder still needs to receive and enter it.

---

## Android / HarmonyOS

### Can't install the APK / HAP

- **Android**: allow "unknown sources" in the install prompt.
- **HarmonyOS**: the debug certificate expires quickly — complete Huawei developer verification first.

### HarmonyOS can't launch 交我办

HarmonyOS does **not** support one-tap login; JAccount web login only. This is a platform limitation.

### Stuck on the login page

1. Confirm the phone can reach `pe.sjtu.edu.cn`.
2. Clear app data and retry.
3. If SJTU SSO is under maintenance, wait and retry.

---

## iOS

| Symptom | Fix |
| --- | --- |
| **"Failed to register bundle identifier"** | Make the bundle ID unique (see [ios.md](./ios.md#set-a-bundle-identifier-optional)) |
| **Won't install / "Untrusted Developer"** | iPhone: **Settings → General → VPN & Device Management** → tap your developer profile → Trust |
| **Login page won't load** | Ensure the iPhone has internet. The app uses JAccount OAuth2; if SJTU SSO is down, wait |
| **Cookie expired** | The app detects this and shows a "re-login" button — tap it |
| **Code signing errors** | Verify the Team ID and that Xcode → Settings → Accounts holds a valid certificate |
| **"No devices registered" (free account)** | Free accounts allow only 1–2 devices. Connect, build and run once and Xcode registers it — but you cannot share the app |

---

## Verifying a downloaded artifact

After downloading from Releases you can check two things.

### 1. Integrity — the file was not altered in transit

The release body lists a SHA256 for every artifact, and you can also download `SHA256SUMS.txt` and check against it:

```bash
# macOS / Linux: place it next to SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
```

```powershell
# Windows PowerShell
Get-FileHash .\SJTURunningMan_<version>_windows.exe -Algorithm SHA256
```

Matching values mean the file is intact.

### 2. Build provenance — built by CI, not uploaded from someone's machine

Every artifact carries a **provenance attestation** issued by GitHub OIDC and bound to a specific commit and workflow run:

```bash
# requires gh CLI 2.49+: https://cli.github.com/
gh attestation verify SJTURunningMan_<version>_windows.exe \
  --repo JackyTJie/SJTURunningMan_Advanced_Edition
```

On success it prints the signing certificate and workflow information. **This attestation cannot be forged locally** — it proves the file was built by GitHub Actions running `release.yml` at that commit.

> Note: provenance only proves *how* something was built, not that the software is trustworthy — anyone able to trigger the workflow can also produce a valid attestation. The Android APK additionally carries a **self-signature** guaranteeing that updates from the same author install over older versions; the two are separate guarantees.

### File reported as damaged / won't open

Check the SHA256 first (step 1 above):

- **Matches** — the file is intact; the problem is almost certainly OS blocking (Windows SmartScreen, macOS Gatekeeper — see the entries below);
- **Doesn't match** — the download was corrupted; just download it again.

## Still stuck?

- Search [Issues](https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition/issues) first.
- Otherwise file one via the [bug template](https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition/issues/new/choose) — and **redact**: no cookies, passwords, captchas, or real names/IDs.
- Security issues go through the private channel in [SECURITY.md](../../SECURITY.md), not a public issue.
