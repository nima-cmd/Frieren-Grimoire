# Frieren Grimoire — how we work in this repo

Read this at the start of every session here.

This is a **tool repo**, not a course repo. The syllabus files it alongside `frieren-spellbook`:
outside the rotation. The working app is the deliverable. That changes how the global
"don't hand me finished code" rule applies — see **Who writes what** below.

---

## Working agreements

- Dev machine is **Linux / Pop!_OS 24.04 / COSMIC on Wayland**. Python 3.12, no Rust.
- **Ask before installing system packages.** Always. Especially anything that claims a device.
- **Build in small vertical slices. Each slice ends with something that runs.** Not a module
  that will matter later — something you can execute tonight and watch produce output.
- **State the plan before doing it.** A short numbered list of what is about to happen, then
  do it. Not a request for permission on each step; a declaration you can interrupt.
- **Commit after each slice**, with a message that explains *why*, not just what.
- Keep `NOTES.md` (hardware truth) and `ledger/index.html` (progress + grimoire) current.
- **Every claim about hardware carries its epistemic status** — `[V]` verified here or read
  from named source, `[R]` reported by a secondary source, `[?]` assumed and unverified.

## Safety rules — not negotiable

- **Never send firmware writes or radio-pairing frames.** Not to the mouse, the dock, the
  receiver or the deck.
- **Never sweep unknown `command_class` / `command_id` values** at a device to see what
  happens. Only send opcodes confirmed from source. The argument is "these specific opcodes
  are known safe," never "the protocol looks harmless."
- **Never enable OpenRGB's SMBus/I2C scanning.** Every documented bricking traces to that
  path. `i2c-dev` is builtin here and `i2c_piix4` already loaded, so withholding modules
  protects nothing — the setting is the only guard.
- **Dry-run by default.** A new frame gets printed as hex and diffed against the reference
  implementation before it is ever sent.
- Character art comes from Nima, in `assets/`. Never generate or recreate it.

---

## Who writes what

The global rule — *"give me the problem and let me write it"* — was written for course repos
where a slow lesson is still a successful one. Here the app is the point, and nine milestones
at "Nima types every line" would take months and compete with the active Spine stage the
whole time. So it applies **by layer**, not uniformly:

| Layer | Examples | Author |
|---|---|---|
| Plumbing | dataclasses, file I/O, argparse, GTK wiring, systemd units | **Claude.** Writing it teaches nothing. |
| Architecture | how device modules plug into the service, where profiles load | **Claude writes, Nima reads.** You cannot invent a structure you have never seen. |
| **Domain logic** | `find_hidraw`, chord expansion, Razer frame + CRC, Loupedeck framing, the validator | **Nima.** These are the ideas. ~15% of the lines, most of the learning. |

## The review protocol — what Kanshou lost

Kanshou has no record of anything taught. The guiding happened in conversation and evaporated;
only the code survived. That is the exact failure the grimoire exists to prevent. So:

1. **Predict before reading.** Before Claude shows a module, Nima says what he thinks it must
   do and roughly how. Thirty seconds. The gap between the prediction and the code *is* the
   lesson.
2. **Claude asks, Nima answers.** After a module lands, Claude asks two or three questions
   about it — *why this order, what breaks if this line goes, what would you change.* Wrong
   answers are the useful ones; they mean re-explain, not move on.
3. **Extend to prove.** Reading produces a feeling of understanding that does not survive a
   blank editor. The test is not "does it make sense" but **"add a feature to it."** You can
   nod along to code you do not understand. You cannot extend it.
4. **It goes in the grimoire the same session.** Every key term, every gotcha, every question
   Nima asks. Organised by topic, never by date. A transcript is not a record.

## Session shape

Open with a **~25–30 minute block and one named deliverable**. Land it, then offer the next
block explicitly. Never ask how long the session is — that converts starting into committing.

**Flag the landing before Nima has to.** Run `date`; never guess the clock.

**The twenty-minute tripwire:** if twenty minutes pass with nothing placed, written or run,
say so out loud. This repo is a tool, and tools are exactly where that drift happens — the
signature to watch for is *building something to remove friction from work not currently
being done.* It must not displace the active Spine stage.
