# Desktop UI checks

These scripts run the production frontend bundle in Chromium with a mocked Tauri
IPC layer. They are for layout and interaction checks only; the real WebView is
covered by the Rust `--ui-smoke-test` command.

```bash
# terminal 1
pnpm build
pnpm exec vite preview --port 4173 --strictPort

# terminal 2
pnpm exec playwright install chromium   # once per machine
node e2e/check.mjs        # functional assertions
node e2e/login.mjs        # incomplete input, IME, auxiliary buttons, errors and duplicate submission
node e2e/celebration.mjs  # success confetti, cleanup, repeat runs and reduced motion
node e2e/preview-fixes.mjs # consent alignment, continuous slider, tile error recovery
node e2e/slider-drag.mjs   # first-frame pointer tracking, including sub-threshold moves
node e2e/live-route.mjs   # live geometry, smooth endpoint, stable viewport, reduced motion
node e2e/screenshot.mjs   # screenshots to /tmp/ui-shots
```

The mock (`mock-init.js`) answers the same command names as `src-tauri/src/commands.rs`.
It never talks to SJTU services. Keep it in sync when a command or payload changes.

`desktop-check.yml` runs all six interaction scripts above in Chromium on push / PR.
Screenshot capture remains manual; failed CI runs upload available diagnostic screenshots and the preview server log.

Set `E2E_BASE_URL` to use a different preview port (default: `http://localhost:4173/`).
