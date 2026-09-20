#!/usr/bin/env python3
"""
inspect_midi.py — summarize a .mid file: tempo, time signature, tracks,
instruments, note counts/ranges. Optionally dump every note event as JSON
in the same shape create_midi.py / edit_midi.py consume.

Usage:
    python inspect_midi.py input.mid
    python inspect_midi.py input.mid --dump-notes > notes.json
"""
import sys
import json
import argparse
import mido
from mido import MidiFile, tempo2bpm

GM_PROGRAMS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano",
    "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2", "Harpsichord",
    "Clavinet", "Celesta", "Glockenspiel", "Music Box", "Vibraphone",
    "Marimba", "Xylophone", "Tubular Bells", "Dulcimer", "Drawbar Organ",
    "Percussive Organ", "Rock Organ", "Church Organ", "Reed Organ",
    "Accordion", "Harmonica", "Tango Accordion", "Acoustic Guitar (nylon)",
    "Acoustic Guitar (steel)", "Electric Guitar (jazz)",
    "Electric Guitar (clean)", "Electric Guitar (muted)",
    "Overdriven Guitar", "Distortion Guitar", "Guitar Harmonics",
    "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)",
    "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1",
    "Synth Bass 2", "Violin", "Viola", "Cello", "Contrabass",
    "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "Synth Strings 1",
    "Synth Strings 2", "Choir Aahs", "Voice Oohs", "Synth Voice",
    "Orchestra Hit", "Trumpet", "Trombone", "Tuba", "Muted Trumpet",
    "French Horn", "Brass Section", "Synth Brass 1", "Synth Brass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe",
    "English Horn", "Bassoon", "Clarinet", "Piccolo", "Flute", "Recorder",
    "Pan Flute", "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)",
    "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)",
    "Lead 7 (fifths)", "Lead 8 (bass + lead)", "Pad 1 (new age)",
    "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)",
    "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)",
    "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)",
    "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bag pipe", "Fiddle",
    "Shanai", "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum",
    "Melodic Tom", "Synth Drum", "Reverse Cymbal", "Guitar Fret Noise",
    "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring",
    "Helicopter", "Applause", "Gunshot",
]


def program_name(p):
    if p is None:
        return "unspecified"
    if 0 <= p < len(GM_PROGRAMS):
        return GM_PROGRAMS[p]
    return f"program {p}"


def note_name(n):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[n % 12]}{n // 12 - 1}"


def collect_notes(track, ticks_per_beat):
    """Return list of dicts: pitch, start (beats), duration (beats), velocity, channel."""
    abs_tick = 0
    open_notes = {}  # (channel, pitch) -> (start_tick, velocity)
    notes = []
    for msg in track:
        abs_tick += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            open_notes[(msg.channel, msg.note)] = (abs_tick, msg.velocity)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            key = (msg.channel, msg.note)
            if key in open_notes:
                start_tick, vel = open_notes.pop(key)
                notes.append({
                    "pitch": msg.note,
                    "start": round(start_tick / ticks_per_beat, 4),
                    "duration": round((abs_tick - start_tick) / ticks_per_beat, 4),
                    "velocity": vel,
                    "channel": msg.channel,
                })
    return notes


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="Path to the .mid file")
    parser.add_argument("--dump-notes", action="store_true",
                         help="Print all note events as JSON instead of the summary")
    args = parser.parse_args()

    mid = MidiFile(args.input)

    if args.dump_notes:
        out = {"ticks_per_beat": mid.ticks_per_beat, "tracks": []}
        for track in mid.tracks:
            notes = collect_notes(track, mid.ticks_per_beat)
            if notes:
                out["tracks"].append({"notes": notes})
        json.dump(out, sys.stdout, indent=2)
        print()
        return

    print(f"File: {args.input}")
    print(f"Type: {mid.type}, Ticks per beat: {mid.ticks_per_beat}, "
          f"Length: {mid.length:.2f}s")

    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                print(f"Tempo: {tempo2bpm(msg.tempo):.1f} BPM")
            elif msg.type == "time_signature":
                print(f"Time signature: {msg.numerator}/{msg.denominator}")
            elif msg.type == "key_signature":
                print(f"Key signature: {msg.key}")

    print(f"\n{len(mid.tracks)} track(s):")
    for i, track in enumerate(mid.tracks):
        name = None
        programs = {}  # channel -> program
        for msg in track:
            if msg.type == "track_name":
                name = msg.name
            if msg.type == "program_change":
                programs[msg.channel] = msg.program

        notes = collect_notes(track, mid.ticks_per_beat)
        print(f"\n  Track {i}: {name or '(unnamed)'}")
        if not notes:
            print("    (no notes — likely a meta/conductor track)")
            continue

        channels = sorted(set(n["channel"] for n in notes))
        for ch in channels:
            ch_notes = [n for n in notes if n["channel"] == ch]
            pitches = [n["pitch"] for n in ch_notes]
            if ch == 9:
                inst = "Percussion (channel 10 / drum kit)"
            else:
                inst = program_name(programs.get(ch))
            print(f"    Channel {ch}: {inst}")
            print(f"      {len(ch_notes)} notes, pitch range "
                  f"{note_name(min(pitches))}-{note_name(max(pitches))} "
                  f"({min(pitches)}-{max(pitches)})")


if __name__ == "__main__":
    main()
