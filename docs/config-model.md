# The config model

Design record for how profiles are described. Written 2026-10-20, **derived from a specific
failure** rather than from preference — see `stream-controller-profile.md` for the audit that
produced it.

## The failure this design exists to prevent

LoupixDeck models a macro as an **imperative list of key events**. Binding `Ctrl+Space` means
hand-assembling four ordered steps:

```
KeyDown ctrl → KeyDown space → KeyUp space → KeyUp ctrl
```

The live config gets this wrong in three of the five hand-built macros:

| Macro | Steps | Fault |
|---|---|---|
| Start Pause | `ctrl↓ space↓ space↑` | **`ctrl↑` missing — modifier stuck on, system-wide** |
| Duplicate Keyframe | `ctrl↓ d↓ ctrl↑ d↑` | releases modifier before key |
| Previous Frame | `ctrl↓ shift↓ left↓ left↑ ctrl↑ shift↑` | release order inconsistent with Next Frame |

Copy and Paste are correct — and they are the two that shipped as presets. **Every macro
assembled by hand has an ordering flaw.** That is not carelessness; it is a data model whose
most likely outcome is a bug, with no validation, no error, and a symptom that surfaces later
somewhere else. (A stuck Ctrl in Krita silently turns the pen into the colour picker.)

**Design rule #1: make the bug unrepresentable, rather than asking the user to be careful.**

---

## Decision 1 — chords are declarative

A binding states the chord. The app derives press and release order.

```json
{ "keys": "Ctrl+Alt+Right" }
```

Expansion is the app's job and is always: modifiers down in order → key down → key up →
modifiers up in **reverse** order. There is no way to express a half-open chord, so the stuck
modifier class is gone by construction. Chord strings are parsed and validated, not trusted.

## Decision 2 — bind to the *action*, not the keystroke

This is the part that matters most, and it is the thing LoupixDeck cannot do.

Krita already stores its own bindings on disk:
- `2D-animation-tutorial/tools/krita-config/kritashortcutsrc` — what is bound
- Krita's `share/krita/actions/*.action` inside the Flatpak — what exists, and its default

So a binding should name the **semantic action** and let the app resolve the keystroke at
runtime:

```json
{ "krita": "insert_hold_frame" }
```

Consequences, all of which are the point:

- **Rebinding in Krita does not break the deck.** The deck follows.
- **Dead bindings are detectable.** `add_duplicate_frame` has no shortcut, so the app can say
  so instead of silently sending nothing.
- **Wrong bindings are detectable.** `Ctrl+D` resolves to Krita's *Deselect*; assigning it to
  a button labelled "Duplicate Keyframe" is a warning the app can raise at edit time.
- The scrub-knob bug (`Ctrl+Shift+Right` vs Krita's `Ctrl+Alt+Right`) **could not have
  happened** — there is no second place for the keystroke to drift out of sync with.

## Decision 3 — three action forms, nothing more

| Form | Meaning | Use for |
|---|---|---|
| `{"krita": "<action_id>"}` | resolve via that app's own config | anything in a supported app |
| `{"keys": "Ctrl+Alt+Right"}` | literal chord | apps we have no resolver for |
| `{"shell": "..."}` | run a command | escape hatch |

`keys` is the fallback, not the default. Each new resolver (`blender`, `musescore`, `godot`)
is additive and optional.

---

## Shape

Profiles are JSON, one file per page, in `profiles/`, version-controlled. Kept close to the
Mac repo's `profiles.json` where it makes sense; it diverges where Linux differs, and that is
fine.

```json
{
  "schema": 1,
  "name": "Krita — animation",
  "match": { "app_id": ["krita", "org.kde.krita"] },

  "knobs": {
    "left.1": {
      "label": "Scrub",
      "ccw":   { "krita": "previous_frame" },
      "cw":    { "krita": "next_frame" },
      "press": { "krita": "toggle_onion_skin" }
    },
    "left.2": {
      "label": "Keyframe",
      "ccw":   { "krita": "previous_keyframe" },
      "cw":    { "krita": "next_keyframe" }
    },
    "left.3": {
      "label": "Hold",
      "ccw":   { "krita": "remove_hold_frame" },
      "cw":    { "krita": "insert_hold_frame" },
      "press": { "krita": "toggle_playback" }
    }
  },

  "touch": {
    "0": { "label": "Duplicate", "action": { "krita": "add_duplicate_frame" } },
    "1": { "label": "Blank",     "action": { "krita": "add_blank_frame" } }
  }
}
```

`match.app_id` is what drives per-app switching. [V] LoupixDeck cannot use this on COSMIC —
it detects focus with `xprop`, which is X11-only. COSMIC's foreign-toplevel protocol gives us
the focused app, so **per-app pages is the feature that justifies the replacement.**

Addressing uses `left.1`-`left.3` / `right.1`-`right.3` for knobs and `0`-`13` for touch
buttons. [V] 14 touch buttons per page, measured from the live config — *not* the 12 that
upstream's generic device table claims for this VID/PID.

---

## Validation — the feature, not a nicety

Every rule below is checkable offline, against files already on disk. This is the single
highest-value thing the app does, and it is worth building **before** any hardware code.

| Check | Example from the live config |
|---|---|
| Action exists | — |
| Action is bound | `add_duplicate_frame` → **unbound in Krita** |
| Chord is not claimed by a different action | `Ctrl+D` → **Krita binds this to Deselect** |
| Chord parses | — |
| Two controls don't send the same chord | — |
| Referenced page exists | physical buttons call `GotoPage(2..7)`; **those pages don't exist** |

Stuck modifiers are absent from this table deliberately — Decision 1 makes them impossible, so
there is nothing to check.

---

## Open questions

1. **Reading `kritashortcutsrc` while Krita is running.** Krita rewrites it on exit, same trap
   as editing LoupixDeck's JSON live. Read-only is safe; never write it behind Krita's back.
2. **The create/toggle modifier tier is undecided.** The existing scheme covers coarse
   (`Alt`), fine (`Ctrl+Alt`) and edit (`Ctrl`), with no tier for creating frames or toggling
   view state — which is exactly why those four actions are unbound. **Nima's call**; the rule
   comes first, the keys follow from it.
3. **Schema compatibility with the Mac `profiles.json`** — worth checking how far it actually
   goes before claiming it.
4. **Does COSMIC's foreign-toplevel protocol expose a usable app id?** Assumed, not verified.
