"""Device discovery.

Devices are found by matching USB vendor/product ID, never by remembering a
node path. Proof that this matters, measured on this machine 2026-10-20:

    18:35   DeathAdder -> hidraw12,13,14,17,19   Dock -> hidraw15,16,18
    21:35   Dock       -> hidraw12,13,14         DeathAdder -> hidraw15,16,17,18,19

The wireless mouse slept and re-enumerated, and the two swapped ranges three
hours apart with nothing unplugged. Code holding "hidraw12" would now be
talking to the dock while believing it had the mouse.
"""

from dataclasses import dataclass
from pathlib import Path

HIDRAW_ROOT = Path("/sys/class/hidraw")
TTY_ROOT = Path("/sys/class/tty")


@dataclass(frozen=True)
class KnownDevice:
    key: str
    name: str
    vid: int
    pid: int
    transport: str  # "hidraw" | "tty"


DEVICES = [
    KnownDevice("mouse", "DeathAdder V2 Pro", 0x1532, 0x007D, "hidraw"),
    KnownDevice("dock", "Mouse Dock Chroma", 0x1532, 0x007E, "hidraw"),
    KnownDevice("deck", "Stream Controller", 0x1532, 0x0D06, "tty"),
    KnownDevice("keyboard", "G915 TKL (receiver)", 0x046D, 0xC545, "hidraw"),
    KnownDevice("speakers", "G560 Speakers", 0x046D, 0x0A78, "hidraw"),
    KnownDevice("aura", "ASUS Aura LED", 0x0B05, 0x1939, "hidraw"),
]


# ---------------------------------------------------------------------------
# YOUR PART. Everything below this line except find_hidraw() is scaffolding.
# ---------------------------------------------------------------------------

def find_hidraw(vid: int, pid: int) -> list[str]:
    """Return every /dev/hidrawN node belonging to this vid/pid, sorted.

    THE EXERCISE -- see frieren/README.md for the problem statement.

    Raw material, verified on this machine:

        $ cat /sys/class/hidraw/hidraw12/device/uevent
        DRIVER=razeraccessory
        HID_ID=0003:00001532:0000007E      <-- bus : vid : pid, hex, zero-padded
        HID_NAME=RAZER Razer Mouse Dock
        ...

    Notes that will bite you if ignored:
      - Not every hidraw entry has a readable uevent. Skip, don't crash.
      - A device usually owns SEVERAL nodes. Return all of them.
      - Sort numerically, not as text, or hidraw2 lands after hidraw19.
    """
    raise NotImplementedError("write me")


# ---------------------------------------------------------------------------
# Scaffolding below -- copy as-is, nothing to solve here.
# ---------------------------------------------------------------------------

def find_tty(vid: int, pid: int) -> list[str]:
    """Return every /dev/ttyACMN node for this vid/pid.

    Different mechanism from hidraw: a tty's `device` symlink points at the USB
    *interface*, so idVendor/idProduct live one directory above it.
    """
    found = []
    for entry in TTY_ROOT.glob("ttyACM*"):
        usb = entry / "device" / ".."
        try:
            v = int((usb / "idVendor").read_text().strip(), 16)
            p = int((usb / "idProduct").read_text().strip(), 16)
        except (OSError, ValueError):
            continue
        if (v, p) == (vid, pid):
            found.append(f"/dev/{entry.name}")
    return sorted(found)


def scan() -> list[tuple[KnownDevice, list[str]]]:
    """Pair every known device with the nodes it currently occupies."""
    out = []
    for dev in DEVICES:
        finder = find_hidraw if dev.transport == "hidraw" else find_tty
        out.append((dev, finder(dev.vid, dev.pid)))
    return out
