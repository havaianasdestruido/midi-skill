#!/usr/bin/env python3
"""
create_midi.py — build a .mid file from a declarative JSON note specification.

Usage:
    python create_midi.py notes.json output.mid

Spec format:
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
        {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 90}
      ]
    }
  ]
}

All timing (start/duration) is in BEATS, not ticks or seconds — this script
handles the conversion, including correctly ordering overlapping notes
(chords) so note_on/note_off events never interleave incorrectly.
"""
import sys
import json
import argparse
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo


def build_track(spec_track, ticks_per_beat):
    channel = spec_track.get("channel", 0)
    program = spec_track.get("program")
    name = spec_track.get("name")

    events = []  # (abs_tick, priority, message)
    # priority: note_off events at the same tick as a note_on should be
    # emitted first, so a new note doesn't get cut short by the previous
    # one's release when they share a boundary tick.
    for note in spec_track["notes"]:
        pitch = note["pitch"]
        velocity = note.get("velocity", 90)
        start_tick = round(note["start"] * ticks_per_beat)
        end_tick = start_tick + round(note["duration"] * ticks_per_beat)
        if end_tick <= start_tick:
            end_tick = start_tick + 1  # guard against zero/negative duration
        events.append((start_tick, 1, Message(
            "note_on", note=pitch, velocity=velocity, channel=channel)))
        events.append((end_tick, 0, Message(
            "note_off", note=pitch, velocity=0, channel=channel)))

    events.sort(key=lambda e: (e[0], e[1]))

    track = MidiTrack()
    if name:
        track.append(MetaMessage("track_name", name=name, time=0))
    if program is not None and channel != 9:
        track.append(Message("program_change", program=program,
                              channel=channel, time=0))

    prev_tick = 0
    for abs_tick, _priority, msg in events:
        delta = abs_tick - prev_tick
        track.append(msg.copy(time=delta))
        prev_tick = abs_tick

    track.append(MetaMessage("end_of_track", time=0))
    return track


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", help="Path to the JSON note spec")
    parser.add_argument("output", help="Path to write the .mid file")
    args = parser.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)

    ticks_per_beat = spec.get("ticks_per_beat", 480)
    tempo_bpm = spec.get("tempo_bpm", 120)
    time_sig = spec.get("time_signature", [4, 4])

    mid = MidiFile(type=1, ticks_per_beat=ticks_per_beat)

    # Conductor track: tempo + time signature, no notes.
    conductor = MidiTrack()
    conductor.append(MetaMessage("set_tempo", tempo=bpm2tempo(tempo_bpm), time=0))
    conductor.append(MetaMessage("time_signature", numerator=time_sig[0],
                                  denominator=time_sig[1], time=0))
    conductor.append(MetaMessage("end_of_track", time=0))
    mid.tracks.append(conductor)

    for spec_track in spec["tracks"]:
        mid.tracks.append(build_track(spec_track, ticks_per_beat))

    mid.save(args.output)

    total_beats = 0
    for t in spec["tracks"]:
        for n in t["notes"]:
            total_beats = max(total_beats, n["start"] + n["duration"])
    print(f"Wrote {args.output}: {len(spec['tracks'])} track(s), "
          f"{tempo_bpm} BPM, {time_sig[0]}/{time_sig[1]}, "
          f"~{total_beats:.2f} beats long.")


if __name__ == "__main__":
    main()
