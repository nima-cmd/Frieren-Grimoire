"""Print what's connected. Run with:  python3 -m frieren"""

from .devices import scan


def main() -> int:
    rows = scan()
    width = max(len(d.name) for d, _ in rows)
    missing = 0

    print()
    for dev, nodes in rows:
        if nodes:
            mark, detail = "✓", ", ".join(nodes)
        else:
            mark, detail = "✗", "not found"
            missing += 1
        print(f"  {mark}  {dev.name:<{width}}  {dev.vid:04x}:{dev.pid:04x}  {detail}")

    print(f"\n  {len(rows) - missing}/{len(rows)} connected\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
