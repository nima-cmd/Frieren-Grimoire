# Razer Nari Ultimate control protocol

Research notes, 2026-10-20. Nothing in this document was sent to the headset or
dongle; the descriptor below was read from the IORegistry, and the commands come
from public projects and from raw Synapse USB captures that were checked byte by
byte.

## Answer

**Yes, haptic intensity is controllable from macOS, and so is the logo LED
on/off.** The command format is public, two independent projects agree on it,
and it shows up verbatim in Synapse USB captures. It is a single 64-byte HID
feature report (ID `0xFF`) on interface 5 of the dongle, which macOS already
exposes and which the dongle's descriptor declares. No new USB capture is needed
for haptics. RGB colour, sidetone and haptic "presets" are less certain (see
[Not yet verified](#not-yet-verified)).

## Transport

| Field | Value |
|---|---|
| Device | Dongle `1532:051A` (the wired headset is `1532:051B`) |
| Interface | 5, top-level collection usage page `0xFF00`, usage `0x01` |
| Request | HID `SET_REPORT`, feature, report ID `0xFF` (USB `wValue = 0x03FF`, `wIndex = 5`) |
| Length | 64 bytes, byte 0 is the report ID `0xFF` |
| Checksum | None (unlike the keyboard's 90-byte Razer report, there is no CRC or transaction ID) |
| Reply | Synapse follows every `SET_REPORT` with a `GET_REPORT` of feature `0xFF` (64 bytes) |

On macOS this maps to `IOHIDDeviceSetReport(dev, kIOHIDReportTypeFeature, 0xFF,
buf, 64)` with `buf[0] = 0xFF`, or hidapi's `hid_send_feature_report(dev, buf,
64)`, opened non-exclusively as in [NOTES.md](../NOTES.md). Both produce exactly
the `wValue = 0x03FF` control transfer the Linux tools use.

## Commands

Every frame starts with a 5-byte wrapper: `ff 0a 00 <dir> 04`, where `<dir>` is
`ff` for a set and `fd` for a query. Bytes 5..8 select the command; the rest is
payload, zero-padded to 64 bytes.

| Command | Bytes (then zeros to 64) | Confidence |
|---|---|---|
| Haptics | `ff 0a 00 ff 04 02 f1 06 20 <en> <level>` | **High**: in Synapse capture, NariCTL, OpenRazer PR |
| Logo LED on/off | `ff 0a 00 ff 04 12 f1 03 71 <00 or ff>` | **High**: in Synapse capture, OpenRazer PR |
| Logo LED brightness | `ff 0a 00 ff 04 12 f1 03 71 <0..100>` | Medium: NariCTL only; the capture only shows `00` and `ff` |
| Logo LED colour | `ff 0a 00 ff 04 12 f1 05 72 <r> <g> <b>` | Low: NariCTL only; the OpenRazer PR author says earlier colour guesses did not work on their unit |
| Mic monitor (sidetone) | `ff 0a 00 ff 04 0e f1 05 01 04 00 <c0..eb>` | Low: NariCTL only, no capture |
| Battery / status query | `ff 0a 00 fd 04 12 f1 02 05`, then `GET_REPORT` | High: four independent battery tools |

Haptics payload: `<en>` is `01` to enable, `00` to disable; `<level>` is
`0x00..0x64` (0..100). The capture "haptic feedback on 20 to 100 off" contains,
in order, `01 14`, `01 1e`, ... `01 64` in steps of 10, and finally `00 64`
(Synapse sends "off" with the last level kept). The motors react to bass in the
audio stream, so the level is a sensitivity and nothing vibrates without audio.

Battery reply (64 bytes, from the projects listed below):

| Byte | Meaning |
|---|---|
| 1..2 | `0f 05` headset live, `01 00` headset off (rest of the reply is then stale cache) |
| 9 | `03` discharging, `04` charge hold, `05` charging, `06` full |
| 12..13 | Battery voltage in mV, big-endian |
| 14 | Firmware battery %, coarse buckets |

The pairing tool uses a different, shorter frame (`ff 19 00 40 ...` to pair,
`... 49` to cancel). Those change the radio pairing and must never be sent by
the app.

## HID descriptor (read from this Mac)

Read from the IORegistry `ReportDescriptor` property of the `IOHIDDevice` for
`1532:051A` (`MaxInput/Output/FeatureReportSize = 64`). Interfaces 0..4 are USB
Audio; interface 5 is HID with three top-level collections:

| Collection | Report ID | Type | Size (incl. ID) | Contents |
|---|---|---|---|---|
| Consumer `0x0C/0x01` | `0x01` | Input | 4 | Vol+ (`E9`), Vol− (`EA`), Mute (`E2`), Prev (`B6`), Play/Pause (`CD`), Next (`B5`) bits |
| Vendor `0xFFC0/0x01` | `0x64` | Input | 2 | One 4-bit value, range 0..13 |
| | `0x65` | Input | 2 | Three 1-bit flags |
| Vendor `0xFF00/0x01` | `0xFF` | Input | 5 | One signed 32-bit value |
| | `0x90` | Input + Output | 15 | 2 bytes (usages `33`, `34`), 16-bit byte count (`0x3B`), 10 data bytes |
| | `0xC4` | Input + Output | 64 | same layout, 59 data bytes |
| | `0xFF` | **Feature** | 64 | 8-bit byte count (`0x3B`), 62 data bytes |
| | `0xE2` | Input | 64 | 8-bit byte count, 62 data bytes |

Feature report `0xFF` is the only feature report on the device and is the one
every tool and Synapse uses. The descriptor calls byte 1 a "byte count", but
every known frame puts `0x0A` there whatever its length, so treat it as a fixed
header byte. The `0x90` / `0xC4` output
reports and the `0xFFC0` inputs are unused by every known tool; the consumer
report exists in the descriptor but the headset does not send it (the wheel and
mute act inside the headset, confirmed earlier by listening).

Raw descriptor, for reference:

```
050c0901a101850109e909ea09e2750195031500250181027505950181039503750109b609cd09b5
8102751595018103c006c0ff0901a101090aa1028564090b7504250d8102750195048103c00914a1
028565091509160917950325018102750595018103c0c00600ff0901a101090aa10285ff7520090b
170100008027ffffff7f8102c00922a102859009337508150026ff008102093481020501093b7510
27ffff000081020600ff090aa102050a1901290a950a750826ff008102c0c00600ff0922a1028590
093395019102093491020501093b751027ffff000091020600ff090aa102050a1901290a950a7508
26ff009102c0c00600ff0922a10285c4093395018102093481020501093b751027ffff0000810206
00ff090aa102050a1901293b953b750826ff008102c0c00600ff0922a10285c40933950191020934
91020501093b751027ffff000091020600ff090aa102050a1901293b953b750826ff009102c0c006
00ff090ca10285ff0501093b9501b102093aa102050a1901293e953eb102c0c00600ff090ca10285
e20501093b95018102093aa102050a1901293e953e8102c0c0c0
```

## Sources

- [openrazer/openrazer#2772](https://github.com/openrazer/openrazer/pull/2772)
  (open, April 2026): kernel driver for haptics and logo LED on the Nari
  Ultimate, tested on hardware; documents the frame layout. Tracks
  [openrazer#974](https://github.com/openrazer/openrazer/issues/974).
- [felixZmn/razer-nari-driver](https://github.com/felixZmn/razer-nari-driver):
  labelled Synapse USBPcap captures (`haptic feedback on 20 to 100 off`,
  `static led on/off`, mic level, mute). These were scanned for this document;
  the haptic and LED frames above appear in them exactly, each as a
  `21 09 ff 03 05 00 40 00` `SET_REPORT` followed by an `a1 01 ff 03 ...`
  `GET_REPORT`.
- [d22592/NariCTL](https://github.com/d22592/NariCTL) (Rust, libusb): haptics,
  LED brightness and colour, sidetone, battery voltage.
- [juanjodarko/razer-nari-pairing](https://github.com/juanjodarko/razer-nari-pairing):
  pairing command extracted from Razer's pairing utility.
- Battery readers: [NariMeter](https://github.com/indina853/NariMeter),
  [razer-nari-linux](https://github.com/srsp2282/razer-nari-linux),
  [RazerNariBatteryLevel](https://github.com/Modzeleczek/RazerNariBatteryLevel).
- Game/chat split on Linux is a PipeWire profile
  ([imustafin/razer-nari-pulseaudio-profile](https://github.com/imustafin/razer-nari-pulseaudio-profile)),
  not a HID command. No project has found a balance command; the two endpoints
  are separate USB audio devices, so balance is a host-side mix (which the app
  already handles through Core Audio).

## Not yet verified

- Whether the haptic level persists across headset power cycles or must be
  re-applied on connect (Synapse may simply re-send it). The app can re-apply on
  connect and wake, as it does for the keyboard, either way.
- RGB colour, LED brightness levels other than `00`/`ff`, sidetone, and
  Synapse's haptic presets. These need a Synapse capture to confirm.
- The `GET_REPORT` reply to a set command (whether it echoes a status byte).

## Recommended approach

1. **Battery query first** (asks for nothing to change): send the status query
   and read the reply. It proves the macOS path (non-exclusive open, feature
   report `0xFF` on the `0xFF00` collection) end to end and gives a battery
   readout for the menu bar.
2. **Haptics** with the exact frames from the capture: `01 32` (50 %), then
   `01 64`, then `00 64` to turn off, with music playing. These are byte-for-byte
   what Synapse sends, so the firmware risk is the same as using Synapse.
3. **Logo LED on/off** with `00` / `ff`.
4. Only if colour or sidetone are wanted: capture Synapse on a Windows PC
   (not a VM; see below) with USBPcap + Wireshark while changing each setting,
   filter on the dongle's address and `usb.setup.wValue == 0x03ff`, and diff
   the frames.

Each of steps 1 to 3 needs the user's go-ahead before anything is sent. Never
send the pairing frames (`ff 19 ...`), and never send guessed values outside the
ranges above. Firmware updates are a separate Razer Windows tool; OpenRazer
maintainers advise against doing them through a VM with USB passthrough.

## Feasibility

High for haptics, LED on/off and battery: about the same effort as the keyboard
lighting code, since it is one fixed-format feature report with no checksum.
Medium for RGB colour and sidetone, which depend on a capture. Low for a
game/chat balance command, which probably does not exist.
