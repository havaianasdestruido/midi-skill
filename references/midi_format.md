# MIDI file format essentials

A `.mid` file does not store audio or even absolute timestamps — it stores a sequence of **events** (mostly "turn this note on/off on this channel with this velocity") with **delta times** between them. Everything else (real time, tempo, bars) is derived from a couple of header values plus tempo meta-messages.

## Structure

- A `MidiFile` has a **type** (0 = single track, 1 = multiple tracks played together, 2 = multiple independent sequences — type 1 is by far the most common for anything beyond a single instrument line).
- `ticks_per_beat` (a.k.a. PPQ, pulses per quarter note): how many ticks make up one quarter-note beat. Common values: 96, 220, 480, 960. Higher = finer timing resolution.
- Each `MidiTrack` is an ordered list of messages. Every message's `time` attribute is **ticks since the previous message on that same track** (not since the start of the file, and not in seconds).
- 16 channels (0-15) exist per file; channel **9** is reserved by the General MIDI standard for percussion — notes on it map to specific drum sounds (see `general_midi.md`) rather than pitches, and a `program_change` on channel 9 is meaningless/ignored by most synths.

## Converting between beats, ticks, and seconds

```
ticks = beats * ticks_per_beat
seconds_per_beat = 60 / tempo_bpm
seconds = beats * seconds_per_beat
```

Tempo is itself stored as a MIDI meta message (`set_tempo`, in **microseconds per quarter note**, not BPM directly):
```
tempo_microseconds = round(60_000_000 / bpm)
bpm = 60_000_000 / tempo_microseconds
```
`mido` provides `mido.bpm2tempo()` / `mido.tempo2bpm()` helpers for this — use them rather than hand-rolling the conversion.

A file can contain multiple `set_tempo` messages (tempo changes mid-piece); if you only care about the overall pace, the first one (usually on track 0, sometimes called the "conductor track") is normally what governs playback until the next one appears.

## Note on/off pairing

A note is represented as a `note_on` followed later by either a `note_off` or a `note_on` with `velocity=0` (both are used in the wild and mean the same thing — "stop this pitch on this channel"). When generating notes programmatically, the reliable approach is to build a flat list of `(absolute_tick, event_type, pitch, velocity, channel)` tuples, **sort by absolute tick** (with note_offs before note_ons at the same tick, to avoid an accidental extra-long note when one note ends exactly as another begins), then walk the sorted list converting each absolute tick back into a delta from the previous event. `scripts/create_midi.py` does exactly this — don't try to interleave note_on/note_off by hand for anything with overlapping notes (chords), it's easy to get the ordering wrong.

## Common meta messages

| Message | Purpose |
|---|---|
| `set_tempo` | microseconds per quarter note (see above) |
| `time_signature` | numerator/denominator (e.g. 4/4), plus clocks-per-click / 32nds-per-quarter (rarely need to touch these last two) |
| `key_signature` | e.g. `'C'`, `'Am'`, `'F#'` — informational only, does not affect playback |
| `track_name` | human-readable label for a track, shown in most DAWs |
| `end_of_track` | required as the final message of every track; `mido` adds this automatically when you use `MidiTrack.append` and save via `MidiFile.save()` only if you don't add it yourself — but it's safest to always end each track with one explicit `MetaMessage('end_of_track')` |

## Note numbers ↔ names

MIDI note number to name: `note_number = 12 * (octave + 1) + pitch_class`, where pitch classes are C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11, and octave numbering follows the common (Yamaha/scientific) convention where middle C = C4 = 60.

| Note | Number | Note | Number | Note | Number |
|---|---|---|---|---|---|
| C4 (middle C) | 60 | C3 | 48 | C5 | 72 |
| D4 | 62 | A3 | 57 | G5 | 79 |
| E4 | 64 | E2 (low guitar E) | 40 | C6 | 84 |
| F4 | 65 | E1 (bass low E) | 28 | | |
| G4 | 67 | | | | |
| A4 (concert pitch, 440Hz) | 69 | | | | |
| B4 | 71 | | | | |

Valid range is 0-127 (C-1 to G9); most acoustic instruments only use a subset of this — check the target instrument's real range before writing very high/low pitches.
