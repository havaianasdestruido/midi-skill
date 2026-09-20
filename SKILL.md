---
name: midi
description: Create, edit, inspect, merge, split, and otherwise manipulate MIDI files (.mid / .midi). Use this whenever the user wants to generate a melody, chord progression, drum pattern, or backing track as a MIDI file; wants to read/inspect an existing .mid file (list tracks, tempo, instruments, notes); wants to transpose, quantize, change tempo/velocity, remap instruments, or otherwise edit a MIDI file; wants to merge multiple MIDI files or split a multi-track file into separate files; or mentions "MIDI", ".mid", ".midi", "note events", "General MIDI", "piano roll", or programmatic music generation. Also use this for converting simple note/chord descriptions (e.g. "C major scale", "a ii-V-I in F") into a playable MIDI file.
---

# MIDI file creation and editing

This skill covers working with the MIDI (Musical Instrument Digital Interface) file format via the `mido` Python library, which is pure-Python and reads/writes standard `.mid` files directly as sequences of timed messages.

## Why mido

`mido` maps almost one-to-one onto the actual bytes of a MIDI file: a `MidiFile` holds a list of `MidiTrack`s, and each track is a list of messages (`note_on`, `note_off`, `program_change`, `control_change`, ...) or meta messages (`set_tempo`, `time_signature`, `track_name`, ...), each with a `time` field measured in **delta ticks since the previous message in that track**. Understanding this delta-time model is the key to not getting confused — see `references/midi_format.md` before writing raw mido code for anything beyond the simplest cases.

Install if not already present:
```bash
pip install mido --break-system-packages
```
No other dependencies are required (this skill does not use `pretty_midi` or `python-rtmidi`; it does not need real-time playback).

## Workflow

1. **Figure out what the user actually wants**: a brand-new composition, an edit of an uploaded file, an inspection/analysis, or a format conversion. This changes which script below applies.
2. **For anything beyond a trivial one-liner, use the bundled scripts** in `scripts/` rather than writing mido code from scratch inline — they already handle the tick-math, tempo conversion, and note-on/off pairing correctly, which is where hand-written MIDI code most often goes wrong.
3. **Always inspect before editing.** If the user gives you an existing MIDI file, run `scripts/inspect_midi.py` on it first so you know its ticks-per-beat, tempo, and channel/instrument layout before changing anything — editing blind is a common source of subtly wrong output (e.g. transposing drum channels, which should never be transposed).
4. **Prefer a declarative note list over raw message assembly.** `scripts/create_midi.py` takes a JSON note spec (see below) rather than requiring you to compute delta-times yourself. Build the note list in your head or in a small Python snippet, dump it to JSON, then call the script. This avoids the classic bug of getting `note_on`/`note_off` ordering or delta-times wrong when notes overlap.
5. **Deliver the file.** Save the resulting `.mid` file to `/mnt/user-data/outputs/` and present it — a MIDI file is not something Claude can usefully describe in prose; the user needs the actual file, and ideally also a plain-language summary of what's in it (key, tempo, structure) so they can sanity-check it without opening a DAW.

## Scripts

### `scripts/create_midi.py` — build a MIDI file from a note list

Takes a JSON note specification and produces a `.mid` file. This is the preferred way to generate new music programmatically, because it separates "what notes happen when" (easy to reason about and to generate for any musical idea) from MIDI's delta-tick encoding (easy to get wrong by hand).

Note spec format (a list of note events, times and durations in **beats**, not ticks or seconds — the script converts):
```json
{
  "tempo_bpm": 120,
  "time_signature": [4, 4],
  "ticks_per_beat": 480,
  "tracks": [
    {
      "name": "Piano",
      "channel": 0,
      "program": 0,
      "notes": [
        {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 90},
        {"pitch": 64, "start": 1.0, "duration": 1.0, "velocity": 90},
        {"pitch": 67, "start": 2.0, "duration": 2.0, "velocity": 100}
      ]
    }
  ]
}
```
- `pitch`: MIDI note number 0-127 (60 = middle C / C4). See `references/midi_format.md` for the full note-name table and `references/general_midi.md` for program numbers per instrument.
- `start` / `duration`: in beats, can overlap (chords = multiple notes with the same `start`).
- `channel` 9 (10th channel, zero-indexed) is the standard drum channel on General MIDI — notes on it are interpreted as percussion sounds, not pitches; don't `program_change` on channel 9.

Usage:
```bash
python scripts/create_midi.py notes.json output.mid
```

### `scripts/inspect_midi.py` — read and summarize a MIDI file

Prints ticks-per-beat, length, tempo changes, time signature, and per-track summaries (name, channel, program/instrument name, note count, pitch range). Add `--dump-notes` to also print every note event as `(pitch, start_beat, duration_beat, velocity, channel)`, which is the format `create_midi.py` and `edit_midi.py` consume — useful for round-tripping an edit.

```bash
python scripts/inspect_midi.py input.mid
python scripts/inspect_midi.py input.mid --dump-notes > notes.json
```

### `scripts/edit_midi.py` — transform an existing file

Non-destructive transforms on a copy of the file. Chainable single-purpose flags:

```bash
python scripts/edit_midi.py input.mid output.mid --transpose 5
python scripts/edit_midi.py input.mid output.mid --tempo 140
python scripts/edit_midi.py input.mid output.mid --velocity-scale 0.8
python scripts/edit_midi.py input.mid output.mid --quantize 16
python scripts/edit_midi.py input.mid output.mid --channel-filter 0,1
python scripts/edit_midi.py input.mid output.mid --program 0:40   # channel:program
```
Run `python scripts/edit_midi.py --help` for the full flag list. By default `--transpose` and `--velocity-scale` skip channel 9 (drums); pass `--include-drums` to override.

### `scripts/merge_split.py` — combine or separate tracks/files

```bash
# Merge several single-track files into one multi-track file, playing in sync
python scripts/merge_split.py merge a.mid b.mid c.mid --out combined.mid

# Split each track of a multi-track file into its own single-track file
python scripts/merge_split.py split input.mid --out-dir split_tracks/
```

## Common requests and how to approach them

- **"Write me a MIDI file of X" (a melody, chord progression, drum beat)**: work out the notes (pitches + beat timings) yourself based on music theory / the user's description, write them as a note spec JSON, run `create_midi.py`. For drum beats, use channel 9 and the standard GM percussion key map in `references/general_midi.md`.
- **"Change the key / transpose this"**: `inspect_midi.py` first to check current key/range, then `edit_midi.py --transpose N` (N = semitones, negative to go down).
- **"Slow it down / speed it up / change the tempo"**: `edit_midi.py --tempo <bpm>`. Note this changes playback tempo, not note timing — the piece still takes the same number of beats.
- **"What instruments/notes are in this file?"**: `inspect_midi.py`, describe the result in plain language (instrument names via GM program table, not just numbers).
- **"Combine these MIDI files / extract just the bass track"**: `merge_split.py`.
- **"Make the drums quieter / fix the timing (quantize)"**: `edit_midi.py --velocity-scale` / `--quantize`, filtered by `--channel-filter` if it should only apply to some tracks.
- **Converting to/from MusicXML, audio (WAV/MP3), or notation**: out of scope for this skill (`mido` only handles the MIDI byte format). Say so, and mention that MusicXML conversion needs `music21` and audio rendering needs a soundfont + synth (e.g. `fluidsynth`) — offer to attempt it with those tools if the user confirms they want it, since they're not bundled here.

## Reference files

- `references/midi_format.md` — MIDI file structure, delta-time/ticks-per-beat math, note number ↔ name table, standard meta messages, why channel 9 is special.
- `references/general_midi.md` — General MIDI program (instrument) number table and the GM percussion key map for channel 9.
