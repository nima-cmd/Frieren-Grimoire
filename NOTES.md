# Hardware notes — Linux

Confirmed facts about this machine and its devices. Same role as the Mac repo's `NOTES.md`:
nothing goes in here unless it has been checked on the actual hardware or read out of a
named source file.

**Convention used throughout:**
- **[V]** verified on this machine or read from named source code, with the command/file shown
- **[R]** reported by a secondary source, reliability noted
- **[?]** assumed or inferred, **not** verified — do not build on these without checking

---

## Machine

[V] Inventory taken 2026-10-22.

| | |
|---|---|
| OS | Pop!_OS 24.04 LTS |
| Session | Wayland, COSMIC (`XDG_SESSION_TYPE=wayland`, `XDG_CURRENT_DESKTOP=COSMIC`) |
| Motherboard | ASUS PRIME B550-PLUS AC (`/sys/devices/virtual/dmi/id/board_name`) |
| Python | 3.12.3 |
| Rust | **not installed** (`cargo: command not found`) |
| User groups | `sudo adm video plugdev render input lpadmin` |

Already present: `python3-gi`, `libadwaita-1-0`, `python3-evdev`, `openrazer-daemon`,
`polychromatic`.
Not present: `gir1.2-gtk-4.0`, `openrgb`, `solaar`, `libratbag`/`ratbagd`, `python3-hid`.

---

## Device inventory

[V] From `lsusb`, `/sys/class/hidraw/*/device/uevent`, and `udevadm info`.

| Device | USB ID | Reachable at | Status |
|---|---|---|---|
| Razer DeathAdder V2 Pro (wireless) | `1532:007d` | `hidraw12,13,14,17,19` | root-only (`crw-------`) |
| Razer Mouse Dock Chroma | `1532:007e` | `hidraw15,16,18` | root-only |
| Razer Stream Controller | `1532:0d06` | **`/dev/ttyACM1`** | **already `crw-rw-rw-`** |
| Logitech receiver (G915) | `046d:c545` | `hidraw6,7,8` | root-only |
| Logitech G560 speakers | `046d:0a78` | `hidraw2` | root-only |
| ASUS Aura LED controller | `0b05:1939` | `hidraw0` | root-only |

Ignored, as instructed: 8BitDo (`2dc8:3109`), Fifine mic (`3142:5060`), all Valve Index
nodes (`28de:*`), hubs.

**`/dev/ttyACM0` is the Valve VR Radio, not the deck.** [V] via `udevadm info`. The deck is
**ACM1**. Don't hardcode ACM1 either — match on `1532:0d06` and resolve the node, because
enumeration order depends on what else is plugged in.

---

## OpenRazer — already installed, and already does most of milestone 4

[V] `openrazer-daemon.service` is `enabled` and running as a **user** unit. Kernel modules
`razermouse` and `razeraccessory` are loaded and bound.

Readable from sysfs **right now**, with no code written:

```
/sys/bus/hid/drivers/razermouse/0003:1532:007D.0010/
    device_type       Razer DeathAdder V2 Pro (Wireless)
    firmware_version  v2.1
    dpi               1800:1800
    poll_rate         500
    charge_level      245
    charge_status     0
/sys/bus/hid/drivers/razeraccessory/0003:1532:007E.000D/
    device_type       Razer Mouse Dock
    firmware_version  v1.1
```

[V] `charge_level` is **raw 0-255, not a percentage** — confirmed in
`razerchromacommon.c:1057-1060`, where the driver returns `arguments[1]` for the caller to
scale 0-255 → 0-100. So `245` ≈ **96%**, not an impossible 245%.

[V] **OpenRazer never touches `/dev/hidraw*` permissions.** Its `99-razer.rules` sets
`GROUP:="plugdev"` on `usb`/`input`/`hid` nodes and `chgrp`s the *sysfs attribute directory*;
a grep of the whole repo finds zero references to `hidraw`. That is exactly why the Razer
hidraw nodes above are still root-only even though the daemon works fine. **We need our own
rule** — see `udev/`.

---

## Razer Chroma protocol — DeathAdder V2 Pro (`1532:007d`)

[V] Read from the OpenRazer driver source (`openrazer/openrazer`, master `477f4d6d`).

### The correction that matters

> **Transaction ID for `1532:007d` is `0x3f` — NOT the `0x1F` in the Mac notes.**

The Mac `NOTES.md` records `0x1F`, which is correct **for the BlackWidow Elite (`1532:0228`)**
and wrong here. [V] All four operations below set `request.transaction_id.id = 0x3f` in their
PID switch-cases in `razermouse_driver.c` (~lines 1610, 2164/2229, 2590, 2836) — four
independent confirmations, not a single-site guess. `0x007C` is the *wired* DeathAdder V2 Pro;
ours is `0x007D`, the wireless one.

Recording this because it is the exact failure the "verify what numbers depend on" rule exists
to catch: a clean derivation from the Mac note would have produced silent no-ops, which look
identical to a wiring problem.

### Report structure

[V] `razercommon.h:124-136`, with `static_assert(sizeof(struct razer_report) == 90)`:

| Offset | Field |
|---|---|
| 0 | `status` |
| 1 | `transaction_id` |
| 2-3 | `remaining_packets` (**big-endian** u16) |
| 4 | `protocol_type` |
| 5 | `data_size` |
| 6 | `command_class` |
| 7 | `command_id` |
| 8-87 | `arguments[80]` |
| 88 | `crc` |
| 89 | `reserved` |

[V] CRC (`razercommon.c:111-119`) = **XOR of bytes 2 through 87 inclusive**, stored at byte 88.
`docs/from-mac/razer_test.py` already implements this correctly.

Sent as a **feature report with report ID `0x00`** (91 bytes on the wire including the ID).
Status byte `0x02` = OK.

### Confirmed-safe commands

[V] From `razerchromacommon.c`:

| Operation | Class | Cmd (get/set) | `data_size` | Arguments |
|---|---|---|---|---|
| DPI | `0x04` | `0x85` / `0x05` | 7 | `varstore, dpi_x_hi, dpi_x_lo, dpi_y_hi, dpi_y_lo, 0, 0` |
| Polling rate | `0x00` | `0x85` / `0x05` | 1 | `0x01`=1000Hz, `0x02`=500Hz, `0x08`=125Hz |
| Battery level | `0x07` | `0x80` | 2 | result in `arguments[1]`, scale 0-255 → 0-100 |
| Charging status | `0x07` | `0x84` | 2 | result in `arguments[1]` (0/1) |

`varstore` `0x00` = NOSTORE (volatile, does not persist to the mouse). Prefer NOSTORE while testing.

### Safety

[V] A grep of `razerchromacommon.c` / `razercommon.c` for firmware/flash opcodes returns
**zero hits** — there is no firmware-write command in this protocol surface.

[V] Pairing commands *do* exist — `razer_attr_write_hyperpolling_wireless_dongle_pair` /
`_unpair` (`razermouse_driver.c:5949-5977`) — but the probe switch-case at lines 7541-7542
creates those sysfs files **only** for `USB_DEVICE_ID_RAZER_HYPERPOLLING_WIRELESS_DONGLE`,
a different product. They are not reachable on the DeathAdder V2 Pro or the Mouse Dock.

**Standing rule: never sweep arbitrary `command_class`/`command_id` values against a device.**
Only send the exact pairs in the table above. The safety argument is "these specific opcodes
are confirmed harmless," not "the protocol is harmless."

### Coexistence with the kernel driver

[V] `razermouse_driver.c:7694` and `razeraccessory_driver.c:2782` both call
`hid_hw_start(hdev, HID_CONNECT_DEFAULT)`, and `HID_CONNECT_DEFAULT` includes
`HID_CONNECT_HIDRAW`. So hidraw stays live *while razermouse is bound* — our app and the
kernel driver are siblings on the same control endpoint, not competitors for ownership.

[?] **The one real hazard:** the device's control endpoint holds one outstanding request at a
time, so if openrazer-daemon polls (battery, etc.) while we send a feature report, the
request/response cycles can interleave and we may read back someone else's reply. Mitigation
is to stop the daemon while our app owns the device. *Not yet reproduced on this machine —
treat as a prediction to test, not a known behaviour.*

---

## Razer Stream Controller (`1532:0d06`)

[V] Hardware is a Loupedeck Live equivalent. Currently driven by **LoupixDeck**
(`/usr/local/bin/loupixdeck`, config `~/.config/LoupixDeck/`), which was *not* running at
inventory time.

[V] Transport: **serial on `/dev/ttyACM1` at 256000 baud**. Firmware 0.2.x performs a
one-time literal HTTP/WebSocket-upgrade handshake as a gate, then drops to raw framing —
every message prefixed with `0x82` (the WebSocket binary-frame opcode), parsed with a
magic-byte length parser. Older 0.1.x firmware used a real TCP WebSocket; that path does not
apply here.

[V] Inner frame: `byte0 = length`, `byte1 = opcode`, `byte2 = transaction ID`, `byte3.. = payload`.
Responses are matched to requests by transaction ID. **ID 0 is reserved** — skip it.

[V] Opcodes (`foxxyz/loupedeck`, `constants.js`):

| Opcode | Meaning | Direction |
|---|---|---|
| `0x00` | `BUTTON_PRESS` | in |
| `0x01` | `KNOB_ROTATE` (signed delta byte) | in |
| `0x4d` / `0x6d` | `TOUCH` / `TOUCH_END` (16-bit BE x/y + touch ID) | in |
| `0x02` | `SET_COLOR` (button ID + R,G,B) | out |
| `0x03` | `SERIAL` | out |
| `0x07` | `VERSION` | out |
| `0x09` | `SET_BRIGHTNESS` (single byte 0-10) | out |
| `0x10` | `FRAMEBUFF` — load offscreen buffer | out |
| `0x0f` | `DRAW` — commit buffer to glass | out |
| `0x1b` | `SET_VIBRATION` | out |

[V] Display: one logical **480×270** panel, RGB565 **little-endian**, addressed as
left (60×270) / centre (360×270) / right (60×270). The 12 touch keys are **90×90** in the
centre zone. Drawing is **two-step**: `FRAMEBUFF` then `DRAW`.

[V] `RazerStreamController` is a near-zero-diff subclass of `LoupedeckLive` in
`foxxyz/loupedeck` — only VID/PID/name differ, the protocol is identical. **Do not conflate
with the Stream Controller X (`1532:0d09`)**, which is a different device entirely (15 keys,
no touchscreen, no knobs).

### Safety

[V] No firmware-flash, bootloader or DFU command found in any reviewed implementation.
[?] `RESET` (`0x06`) and `MCU` (`0x0d`) exist as opcodes but are **undocumented and sent by
neither reference implementation**. **Do not send them.**

[R] LoupixDeck's maintainer reports this exact chip truncates bit 11 of the RGB565 word,
giving red ~16 levels while green/blue stay full. Hardware-measured by one person, not
independently reproduced — expect it, verify before designing art around it.

[R] Firmware 0.2.26 reportedly does not work on Linux; 0.2.23 is the suggested fallback
(`foxxyz/loupedeck` README). **Our device's firmware version has not been read yet** — do
that early with `VERSION` (`0x07`), since it is cheap and decides whether we hit this.

### Reference implementations

| Repo | Lang | Use for |
|---|---|---|
| `foxxyz/loupedeck` | JS | canonical protocol state machine |
| `RadiatorTwo/LoupixDeck` | C# / Avalonia, MIT | `RazerStreamControllerDevice.cs` — quirks for *this exact* chip |

---

## OpenRGB — not installed; the risk is real but narrow

[V] Not installed. Relevant because it is the proposed one-stop lighting backend for the
G915, G560 and ASUS Aura.

**The documented damage is confined to the SMBus/i2c path**, and that path is a *separate,
optional feature* from USB device control:
- [V] DDR5 SPD EEPROM corruption — GitLab meta-issue #4934, mechanism detailed in #1171
  (concurrent SMBus access racing on multi-byte EEPROM page-address transactions).
  **This board is B550 → DDR4**, so the active DDR5 thread does not directly apply.
- [R] Gigabyte Z390 shutdown-and-won't-restart (#213) and MSI Mystic Light controller
  bricking (#389, #4092, recovery needed an external Nu-Link programmer). Both are
  **SMBus motherboard controllers**. This board is ASUS, and its Aura controller is USB.
- [V] **No bricking of any USB HID device was found** in any source.

[V] The ASUS Aura controller here is `0b05:1939` on **`hidraw0`** — plain USB HID. It does
not sit on the SMBus at all, so controlling it cannot touch RAM SPD.

### The mitigation is NOT what the internet says

The usual advice is "don't load `i2c-dev`/`i2c-piix4`." **That does not work on this machine**:

[V] `i2c-dev` is **compiled into the Pop!_OS kernel** (`modinfo i2c-dev` → `filename: (builtin)`),
and `i2c_piix4` is **already loaded**. Three SMBus adapters are live right now:

```
i2c-0  SMBus PIIX4 adapter port 0 at 0b00
i2c-1  SMBus PIIX4 adapter port 2 at 0b00
i2c-2  SMBus PIIX4 adapter port 1 at 0b20
(i2c-3..8 are NVIDIA GPU adapters)
```

So the SMBus surface is present and writable regardless of what we install. **Protection must
come from OpenRGB's own configuration — disabling I2C/SMBus detection — not from withholding
kernel modules.** If OpenRGB is installed, it must be run with SMBus scanning off and its
"SMBus Tools / Dump Device" debug page left alone; that page is hidden by default precisely
because of issue #213.

### Other OpenRGB findings

[V] Its FAQ states it uses **the OpenRazer kernel driver** for Razer devices and does not need
the daemon. Consequence: it will not fight openrazer-daemon for the USB device, but both
writing lighting is last-write-wins. [V] OpenRazer maintainer `lah7` (issue #1908) confirms
they coexist if OpenRazer's effects/persistence are left off.

[V] G560 (`046d:0a78`) supported, plain USB.

[V] **The keyboard is a G915 TKL** — confirmed 2026-10-22 by physical inspection (no numpad).
This matches the community kernel-patch mapping of receiver PID `c545` to the TKL, and
resolves the discrepancy with merge !713 (which covers the *full-size* G915). TKL support
landed separately in !929 / !1029, with documented limits: **only "Direct" LED mode works,
and Bluetooth mode is unsupported.** [R] Open bug #5022 — a newer "G915X TKL" is sometimes
misdetected as a plain G915; unknown whether this unit is affected.

[R] Known wireless-mode quirk from the G915 merge request: pressing an M key resets lighting
to the keyboard's stored profile, and after some time all keys switch off until an M key is
pressed or the keyboard is power-cycled.

---

---

## The G915 TKL has no G-keys — milestone 7 needs rethinking

[V] Confirmed by inspection. The full-size G915 carries a dedicated **G1-G5** strip down the
left edge; the TKL deletes that strip along with the numpad. `ESC` sits directly above
`` ` ``, and the top row begins at F1.

The brief's milestone 7 — *"macros + G-Shift across G915 G-keys"* — therefore has **no
physical G-keys to bind.** Three candidate replacements, none yet tested:

1. **The F13-F24 route.** [V] The receiver's evdev node (`/dev/input/event5`) advertises
   `KEY_F13` through `KEY_F24` plus `KEY_PROGRAM`. This is exactly the trick the Mac app used
   (routing spells through spare codes F16-F20), so the concept carries over intact.
   [?] **Caveat: a code appearing in the capability bitmap only means the receiver *can*
   report it — not that any physical key sends it.** On a TKL without G HUB, probably nothing
   triggers these. Must be tested by grabbing the device and watching for events.
2. **Repurpose existing keys via evdev grab + uinput.** Works on Wayland and can tell which
   device a key came from, which is the thing the Mac `CGEvent` tap explicitly could not do.
   Costs whatever key gets repurposed.
3. **Put the spells on the Stream Controller instead** — 12 touch buttons and 6 dials, all
   free per the 2026-08-27 survey. Arguably the better home for them anyway.

The `FN` key is handled in keyboard firmware and is [?] likely not remappable, same as the
BlackWidow's fn on the Mac side.

---

## Open questions

1. ~~G915 vs G915 TKL~~ — **resolved 2026-10-22: TKL.** See above.
2. **Does anything on the TKL actually emit F13-F24?** Decides whether milestone 7 route 1
   is real. Test by grabbing `/dev/input/event5` and pressing every key and FN combination.
3. **Stream Controller firmware version** — read with `VERSION` (`0x07`); decides whether the
   0.2.26-on-Linux problem bites.
4. **Daemon/hidraw interleaving** — predicted above, not yet reproduced.
5. **`charge_level` 245 ≈ 96%** — scaling is confirmed from source, but has not been
   cross-checked against the mouse's own battery indicator.
