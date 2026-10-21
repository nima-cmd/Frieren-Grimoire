#!/usr/bin/env python3
"""Milestone 1 proof of concept: set a static color on a Razer BlackWidow Elite.

Tries every HID interface of the keyboard and both candidate transaction IDs,
reads back the response status, and stops at the first combination that works.

Protocol reference: OpenRazer driver/razerkbd_driver.c + razerchromacommon.c
(BlackWidow Elite 0x0228 uses transaction ID 0x1F for matrix effects).

Usage: python3 razer_test.py [RRGGBB]
"""
import ctypes
import sys
import time

import hid

# hidapi on macOS opens devices exclusively (kIOHIDOptionsTypeSeizeDevice) by
# default, which fails for a keyboard the system is using. The Python binding
# doesn't expose the switch, but the bundled C library exports it.
if sys.platform == "darwin":
    _lib = ctypes.CDLL(hid.__file__)
    _lib.hid_init()
    _lib.hid_darwin_set_open_exclusive(ctypes.c_int(0))

VENDOR_ID = 0x1532
PRODUCT_ID = 0x0228
TRANSACTION_IDS = [0x1F, 0x3F]

STATUS = {0x00: "new", 0x01: "busy", 0x02: "OK", 0x03: "failed", 0x04: "timeout", 0x05: "not supported"}


def build_report(transaction_id, command_class, command_id, args):
    """Build the 90-byte Razer report (without the leading HID report ID)."""
    report = bytearray(90)
    report[0] = 0x00                 # status
    report[1] = transaction_id
    report[2] = 0x00                 # remaining packets (2 bytes, big endian)
    report[3] = 0x00
    report[4] = 0x00                 # protocol type
    report[5] = len(args)            # data size
    report[6] = command_class
    report[7] = command_id
    report[8:8 + len(args)] = bytes(args)
    crc = 0
    for b in report[2:88]:
        crc ^= b
    report[88] = crc
    return report


def static_color_report(transaction_id, r, g, b):
    # Extended matrix effect: VARSTORE, BACKLIGHT_LED, STATIC, 0, 0, 1, R, G, B
    return build_report(transaction_id, 0x0F, 0x02, [0x01, 0x05, 0x01, 0x00, 0x00, 0x01, r, g, b])


def try_interface(info, transaction_id, rgb):
    dev = hid.device()
    try:
        dev.open_path(info["path"])
    except OSError as e:
        return None, f"open failed ({e})"
    try:
        report = static_color_report(transaction_id, *rgb)
        sent = dev.send_feature_report(bytes([0x00]) + report)
        if sent < 0:
            return None, "send_feature_report failed"
        time.sleep(0.01)  # OpenRazer waits ~600-800us; be generous
        resp = dev.get_feature_report(0x00, 91)
        # hidapi on macOS returns the report ID as the first byte
        if len(resp) == 91:
            resp = resp[1:]
        if len(resp) < 90:
            return None, f"short response ({len(resp)} bytes)"
        status = resp[0]
        echo_ok = resp[1] == transaction_id and resp[6] == 0x0F and resp[7] == 0x02
        return status, f"status=0x{status:02X} ({STATUS.get(status, '?')}), echo {'matches' if echo_ok else 'mismatch'}"
    except OSError as e:
        return None, f"I/O error ({e})"
    finally:
        dev.close()


def main():
    hexcolor = sys.argv[1] if len(sys.argv) > 1 else "00C8B4"
    rgb = tuple(int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))

    infos = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    if not infos:
        print("BlackWidow Elite (1532:0228) not found.")
        return 1

    # One attempt per distinct path (each path is one USB interface).
    seen, interfaces = set(), []
    for info in sorted(infos, key=lambda i: i["interface_number"]):
        if info["path"] not in seen:
            seen.add(info["path"])
            interfaces.append(info)

    print(f"Setting static color #{hexcolor.upper()} ...")
    for txid in TRANSACTION_IDS:
        for info in interfaces:
            status, msg = try_interface(info, txid, rgb)
            print(f"  interface {info['interface_number']}  txid 0x{txid:02X}: {msg}")
            if status == 0x02:
                print(f"\nWORKING: interface {info['interface_number']}, transaction ID 0x{txid:02X}")
                return 0
    print("\nNo combination succeeded.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
