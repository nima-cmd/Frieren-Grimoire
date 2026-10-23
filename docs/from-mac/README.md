# Reference material from the macOS app

Everything in this directory was copied from **https://github.com/nima-cmd/Razer-Frieren**
(private), the macOS/SwiftUI version of this project, at its state of **2026-10-20**.

**It is reference, not source.** Nothing here is built or run by the Linux app. The Swift
package (`RazerKit/`), the SwiftUI app (`App/`) and the Xcode project were deliberately
*not* copied — they are macOS-only and remain in the Mac repo.

**Never commit or push to the Mac repo from here.**

## What each file is, and how much of it still applies

| File | Origin | Status for Linux |
|---|---|---|
| `NOTES.md` | Mac repo root | **Mostly does not apply.** See below. |
| `nari-protocol.md` | Mac repo `docs/` | Protocol record for a Razer Nari Ultimate headset. **That headset is not on this machine.** Kept only because the "never send pairing frames" rule derives from it. |
| `razer_test.py` | Mac repo root | **The most reusable file here.** See below. |
| `extract_layout.py` | Mac repo `tools/` | Technique is reusable, output is not — it emits *Swift* for a *BlackWidow Elite*. |
| `import_artwork.sh` | Mac repo `tools/` | **Dead on Linux** — uses `sips` (macOS-only) and writes into a `.app` bundle. Kept only for its mapping of source image → role. |

### `NOTES.md` — read with care

It documents a **Razer BlackWidow Elite keyboard (1532:0228)** and a **Nari Ultimate headset
(1532:051A)**. *Neither device is connected to the Linux machine.* The keyboard here is a
Logitech G915.

What genuinely transfers:
- the 90-byte Chroma report framing and its CRC,
- the per-key matrix upload method (class `0x0F`),
- the general shape of the `profiles.json` schema.

What does **not** transfer: every hidutil remap, the `CGEvent` tap, Core Audio, Input
Monitoring / Accessibility grants, `SMAppService`, and code signing. All macOS-specific.

**One concrete error it would have caused.** Its Chroma section states transaction ID
`0x1F`, correct for the BlackWidow Elite. The DeathAdder V2 Pro on this machine uses
**`0x3f`**. Applying the Mac note unchanged would have produced silent no-ops. See the
root `NOTES.md` for the verification.

### `razer_test.py` — the seed of the Linux Razer module

Its `build_report()` was checked byte-for-byte against OpenRazer's `driver/razercommon.{c,h}`
on 2026-10-22 and is **correct**: the struct layout matches, and the CRC (XOR over bytes
2..87 inclusive, stored at byte 88) matches `razer_crc()` exactly.

To reuse it, three things change — and nothing else:
1. delete the `sys.platform == "darwin"` block (lines 21-24) — that workaround is for
   macOS exclusive-open and is meaningless on Linux;
2. `PRODUCT_ID = 0x0228` → `0x007D`;
3. `TRANSACTION_IDS` → `[0x3F]` (it already *contains* `0x3F` as a candidate, which is why
   the brute-force loop in this script would have stumbled onto the right answer anyway).
