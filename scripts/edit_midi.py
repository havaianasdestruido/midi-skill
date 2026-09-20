#!/usr/bin/env python3
"""
edit_midi.py — apply one or more transforms to a copy of a .mid file.

Usage:
    python edit_midi.py input.mid output.mid --transpose 5
    python edit_midi.py input.mid output.mid --tempo 140
    python edit_midi.py input.mid output.mid --velocity-scale 0.8
    python edit_midi.py input.mid output.mid --quantize 16
    python edit_midi.py input.mid output.mid --channel-filter 0,1
    python edit_midi.py input.mid output.mid --program 0:40

Multiple flags can be combined in one call; they are applied in the order:
channel-filter -> transpose -> velocity-scale -> quantize -> program -> tempo.

By default --transpose and --velocity-scale skip channel 9 (the standard
General MIDI drum channel), since shifting drum notes changes WHICH drum
sound plays rather than its pitch. Pass --include-drums to apply to
channel 9 as well.
"""
import argparse
import mido
from mido import MidiFile, bpm2tempo


def parse_channel_list(s):
    return set(int(x) for x in s.split(","))


def parse_program_map(items):
    """['0:40', '1:0'] -> {0: 40, 1: 0}"""
    mapping = {}
    for item in items:
        ch, prog = item.split(":")
        mapping[int(ch)] = int(prog)
    return mapping


def apply_channel_filter(mid, keep_channels):
    for track in mid.tracks:
        new_track = []
        for msg in track:
            if hasattr(msg, "channel") and msg.channel not in keep_channels:
                continue
            new_track.append(msg)
        track[:] = new_track


def apply_transpose(mid, semitones, include_drums):
    for track in mid.tracks:
        for msg in track:
            if msg.type in ("note_on", "note_off"):
                if msg.channel == 9 and not include_drums:
                    continue
                msg.note = max(0, min(127, msg.note + semitones))


def apply_velocity_scale(mid, factor, include_drums):
    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                if msg.channel == 9 and not include_drums:
                    continue
                msg.velocity = max(1, min(127, round(msg.velocity * factor)))


def apply_quantize(mid, division):
    """Snap note_on/note_off start times to the nearest 1/division note.
    division=16 means snap to sixteenth notes."""
    step_ticks = mid.ticks_per_beat * 4 / division  # quarter note = ticks_per_beat
    for track in mid.tracks:
        abs_tick = 0
        events = []
        for msg in track:
            abs_tick += msg.time
            events.append([abs_tick, msg])
        for e in events:
            if e[1].type in ("note_on", "note_off"):
                e[0] = round(e[0] / step_ticks) * step_ticks
        events.sort(key=lambda e: e[0])
        prev = 0
        new_track = []
        for abs_tick, msg in events:
            delta = max(0, round(abs_tick - prev))
            new_track.append(msg.copy(time=delta))
            prev = abs_tick
        track[:] = new_track


def apply_program_map(mid, mapping):
    for track in mid.tracks:
        for msg in track:
            if msg.type == "program_change" and msg.channel in mapping:
                msg.program = mapping[msg.channel]
        # If a channel in the mapping never had a program_change, insert one
        # at the start of the first track that uses that channel.
    seen = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == "program_change":
                seen.add(msg.channel)
    for ch, prog in mapping.items():
        if ch not in seen and ch != 9:
            for track in mid.tracks:
                if any(hasattr(m, "channel") and m.channel == ch for m in track):
                    track.insert(0, mido.Message("program_change", program=prog,
                                                  channel=ch, time=0))
                    break


def apply_tempo(mid, bpm):
    new_tempo = bpm2tempo(bpm)
    found = False
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                msg.tempo = new_tempo
                found = True
    if not found:
        mid.tracks[0].insert(0, mido.MetaMessage("set_tempo", tempo=new_tempo, time=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--transpose", type=int, help="Semitones, can be negative")
    parser.add_argument("--tempo", type=float, help="New tempo in BPM")
    parser.add_argument("--velocity-scale", type=float, help="Multiply all velocities, e.g. 0.8")
    parser.add_argument("--quantize", type=int, help="Snap notes to nearest 1/N note, e.g. 16")
    parser.add_argument("--channel-filter", type=parse_channel_list,
                         help="Comma-separated channels to KEEP, e.g. 0,1")
    parser.add_argument("--program", action="append", default=[],
                         help="channel:program, e.g. 0:40. Repeatable.")
    parser.add_argument("--include-drums", action="store_true",
                         help="Apply transpose/velocity-scale to channel 9 as well")
    args = parser.parse_args()

    mid = MidiFile(args.input)

    if args.channel_filter is not None:
        apply_channel_filter(mid, args.channel_filter)
    if args.transpose is not None:
        apply_transpose(mid, args.transpose, args.include_drums)
    if args.velocity_scale is not None:
        apply_velocity_scale(mid, args.velocity_scale, args.include_drums)
    if args.quantize is not None:
        apply_quantize(mid, args.quantize)
    if args.program:
        apply_program_map(mid, parse_program_map(args.program))
    if args.tempo is not None:
        apply_tempo(mid, args.tempo)

    mid.save(args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
