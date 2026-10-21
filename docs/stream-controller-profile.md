# Stream Controller — the Krita animation page

Audit of the **existing** LoupixDeck configuration against **Krita's actual bindings**,
2026-10-20. This is the design record for the deck page; the Frieren Grimoire app will
eventually load this same layout, but it is useful *today* through LoupixDeck's GUI.

Sources checked, all first-party:
- `~/.config/LoupixDeck/config_razer-stream-controller_*.json` and `macros.json`
- `2D-animation-tutorial/tools/krita-config/kritashortcutsrc`
- Krita's own action definitions inside the Flatpak:
  `/var/lib/flatpak/app/org.kde.krita/x86_64/stable/active/files/share/krita/actions/*.action`

---

## The headline: most of the animation page does not work

The deck *looks* configured for animation — three labelled knobs and six touch buttons. In
fact **one of three knobs and four of six touch buttons are dead or actively wrong in Krita.**

| Deck control | Macro sends | Krita's state | Verdict |
|---|---|---|---|
| Knob 1 "Scrub" ← → | `Ctrl+Shift+Left/Right` | `kritashortcutsrc` binds `previous_frame`/`next_frame` to **`Ctrl+Alt+Arrow`** | ❌ **wrong keys — does nothing** |
| Knob 2 "Key Frame" ← → | `Alt+Left/Right` | `previous_keyframe`/`next_keyframe` = `Alt+Arrow` | ✅ works |
| Knob 3 "Hold" ← → | `Ctrl+Left/Right` | `remove_hold_frame`/`insert_hold_frame` = `Ctrl+Arrow` | ✅ works |
| Touch 0 "Duplicate Keyframe" | `Ctrl+D` | `add_duplicate_frame` has **no shortcut**; `Ctrl+D` is Krita's **Deselect** | ❌ **wrong action fires** |
| Touch 1 "Blank Keyframe" | `Ctrl+Alt+B` | `add_blank_frame` has **no shortcut** | ❌ nothing bound |
| Touch 4 "Start/Pause" | `Ctrl+Space` | `toggle_playback` has **no shortcut** | ❌ nothing bound **+ see below** |
| Touch 8 / 9 Copy / Paste | `Ctrl+C` / `Ctrl+V` | standard | ✅ works |
| Touch 11 "Play" | `F5` | unverified | ❓ |

[V] **Every one of `add_duplicate_frame`, `add_blank_frame`, `toggle_playback` and
`toggle_onion_skin` ships with `(none)` as its default shortcut** — read directly out of
Krita's `.action` files. `kritashortcutsrc` binds only six actions, and none of those four
are among them. So the deck is sending key combinations that nothing in Krita listens for.

### The one that can bite you

[V] The **"Start Pause" macro never releases Ctrl.** Its steps are:

```
KeyDown ctrl
KeyDown space
KeyUp   space
          <- no KeyUp ctrl
```

Compare Copy, which is correct: `ctrl↓ c↓ c↑ ctrl↑`.

Because LoupixDeck injects through `uinput` at kernel level, that Ctrl stays **logically held
down system-wide** until something else releases it. In Krita, held Ctrl is the **colour
picker** modifier — so after pressing Play, the next pen stroke samples colour instead of
drawing. If you have ever hit a spell of "Krita suddenly behaving strangely," this is a prime
suspect.

Two lesser instances of the same sloppiness, both probably harmless:
- "Duplicate Keyframe" releases in the order `ctrl↑ d↑` — modifier released before the key.
- "Previous Frame" releases `ctrl↑ shift↑`; "Next Frame" releases `shift↑ ctrl↑`. Inconsistent.

---

## The gap in the shortcut scheme

The existing scheme is deliberate and worth preserving ([V] from
`tools/krita-config/README.md`):

| Modifier | Meaning | Bound |
|---|---|---|
| `Alt` | **coarse** — keyframe to keyframe | ✅ |
| `Ctrl+Alt` | **fine** — single frame | ✅ |
| `Ctrl` | **edit** — change a duration | ✅ |
| — | **create / toggle** — new frames, view states | ❌ **no tier exists** |

Frame *creation* (duplicate, blank) and *view toggles* (onion skin, playback) are a fourth
category the scheme never grew a tier for. That is the actual design question, and it is
Nima's to answer — the rule should come first, then the keys fall out of it. One candidate
worth considering: `Ctrl+Alt+<letter>` for creation, since `Ctrl+Alt` already means "precise /
per-frame", and the deck is *already* sending `Ctrl+Alt+B` for blank frame — binding that one
in Krita costs nothing and makes an existing button work.

**`toggle_onion_skin` is not on the deck at all and has no shortcut**, despite the lesson notes
calling it something used "constantly while in-betweening". That is the single highest-value
addition available.

---

## Wayland blocks per-app switching — and this is the app's reason to exist

[V] `AppSwitchingEnabled: false`, `AppPageBindings: []`, `ContextRules: []` in the live config.

[R] Upstream, LoupixDeck detects the focused window by shelling out to
`xprop -root -spy _NET_ACTIVE_WINDOW`, gated on `$DISPLAY`. That is **X11-only**. This machine
runs COSMIC on Wayland, so the syllabus to-do *"wire `AppSwitchingEnabled` + `AppPageBindings`
so the deck follows the active application"* **cannot be completed in LoupixDeck at all.**
Pages must be changed by hand on the eight physical buttons.

This is precisely the gap the Frieren Grimoire fills: COSMIC exposes a foreign-toplevel
protocol, so our app *can* follow the focused window where LoupixDeck structurally cannot.
**Per-app pages is the feature that justifies replacing LoupixDeck** — not lighting, not
icons. Worth remembering when scoping milestone 6.

---

## Capacity, as actually measured

[V] From the live config, correcting the syllabus:

| Surface | Count | Used | Free |
|---|---|---|---|
| Touch buttons | **14** per page | 6 on page 1 | 8 |
| Left rotaries | 3 × (L/R/press) | 6 of 9 slots | **3 presses all free** |
| Right rotaries | 3 × (L/R/press), 2 pages | **0** | all 18 slots |
| Physical buttons | 8 (ids 6–13) | all 8 = page nav | 0 |
| Touch pages | 1 defined | — | buttons reference pages 2–7 that **do not exist** |

Two corrections to `nima-cmd-work/SYLLABUS.md`, which is stale on this:
1. It says *"To do: bind one rotary to hold-frame lengthen/shorten."* **Already done** — left
   knob 3, and it is one of the three things that actually works.
2. It says 14 touchscreen buttons with **"none assigned"**. Six are assigned.

The three **rotary press** slots are the best free real estate: a knob you are already holding
for scrub/keyframe/hold, with an unused click each.

---

## Fix order (cheapest first, nothing requires building anything)

1. **Fix "Start Pause"** — add the missing `KeyUp ctrl`. Stops a system-wide stuck modifier.
2. **Fix "Scrub"** — change `Ctrl+Shift+Arrow` → `Ctrl+Alt+Arrow`. Revives knob 1.
3. **Decide the create/toggle tier**, then bind in Krita: `add_duplicate_frame`,
   `add_blank_frame`, `toggle_playback`, `toggle_onion_skin`.
4. **Repoint** touch 0/1/4 at the new bindings; add onion skin to a rotary press.

**Edit through LoupixDeck's GUI, never the JSON by hand** — it is running and will overwrite
the file on exit. (Standing rule from the syllabus, verified 2026-08-27.)
