# Exercise 1 — device discovery

Write `find_hidraw(vid, pid)` in `devices.py`. Everything else is already there.

Run it with:

```
python3 -m frieren
```

Right now that raises `NotImplementedError`. When you're done it should print all six
devices with the nodes they're on.

## The problem

Given a vendor ID and product ID, find every `/dev/hidrawN` node that belongs to that device.

Each node has a matching directory in sysfs:

```
/sys/class/hidraw/hidraw12/device/uevent
```

which contains, among other lines:

```
HID_ID=0003:00001532:0000007E
```

That's `bus : vendor : product`, hexadecimal, zero-padded to 8 digits. For the mouse you're
looking for vendor `1532` and product `007D` — so the line you want ends `:00001532:0000007D`.

Your function returns a list like `["/dev/hidraw15", "/dev/hidraw16", ...]`.

## Three things that will catch you

1. **Some entries have no readable `uevent`.** Skip them rather than crashing — the device
   may have vanished between listing the directory and reading the file.
2. **One device owns several nodes.** The mouse has five. Return all of them.
3. **Sorting `hidraw2` and `hidraw19` as text puts them in the wrong order.** Sort by the
   number.

## Why match on IDs instead of just remembering the path

Measured on your machine today, nothing unplugged, three hours apart:

```
18:35   DeathAdder → hidraw12,13,14,17,19     Dock → hidraw15,16,18
21:35   Dock       → hidraw12,13,14           DeathAdder → hidraw15,16,17,18,19
```

The wireless mouse slept, re-enumerated, and the two swapped ranges. Code holding `hidraw12`
would now be sending mouse commands to the dock.

## When it works

You should see six ✓. If the Stream Controller shows ✗, check it's powered — the `tty` half
is already written and was verified working.

Then: does the output still agree with reality after you put the mouse to sleep and wake it?
That's the actual test, and it's the whole reason the function exists.
