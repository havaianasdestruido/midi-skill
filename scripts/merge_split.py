#!/usr/bin/env python3
"""
merge_split.py — combine multiple MIDI files into one, or split a
multi-track MIDI file into separate single-track files.

Usage:
    # Merge: all input files play in sync, each becomes its own track(s)
    # in the output. All inputs are re-quantized to the ticks_per_beat of
    # the FIRST file (their timing is rescaled if they differ).
    python merge_split.py merge a.mid b.mid c.mid --out combined.mid

    # Split: each track of the input becomes its own single-track .mid
    # file, keeping tempo/time-signature info in every output file.
    python merge_split.py split input.mid --out-dir split_tracks/
"""
import os
import argparse
import mido
from mido import MidiFile, MidiTrack, MetaMessage


def rescale_track(track, factor):
    if factor == 1.0:
        return track
    new_track = MidiTrack()
    for msg in track:
        new_track.append(msg.copy(time=round(msg.time * factor)))
    return new_track


def merge(input_paths, out_path):
    files = [MidiFile(p) for p in input_paths]
    base_tpb = files[0].ticks_per_beat

    out = MidiFile(type=1, ticks_per_beat=base_tpb)
    for path, f in zip(input_paths, files):
        factor = base_tpb / f.ticks_per_beat
        for track in f.tracks:
            scaled = rescale_track(track, factor)
            # Tag the track with its source filename if it has no name yet.
            if not any(m.type == "track_name" for m in scaled):
                label = MidiTrack()
                label.append(MetaMessage("track_name",
                                          name=os.path.splitext(os.path.basename(path))[0],
                                          time=0))
                label.extend(scaled)
                scaled = label
            out.tracks.append(scaled)

    out.save(out_path)
    print(f"Merged {len(input_paths)} file(s) into {out_path} "
          f"({len(out.tracks)} tracks total, {base_tpb} ticks/beat).")


def split(input_path, out_dir):
    mid = MidiFile(input_path)
    os.makedirs(out_dir, exist_ok=True)

    # Find conductor-level meta info (tempo/time-sig) to copy into every
    # split file so each one is independently playable at the right speed.
    global_meta = []
    for track in mid.tracks:
        for msg in track:
            if msg.type in ("set_tempo", "time_signature", "key_signature"):
                global_meta.append(msg.copy(time=0))

    written = []
    for i, track in enumerate(mid.tracks):
        has_notes = any(m.type == "note_on" for m in track)
        if not has_notes:
            continue  # skip pure meta/conductor tracks
        out = MidiFile(type=0, ticks_per_beat=mid.ticks_per_beat)
        new_track = MidiTrack()
        for m in global_meta:
            new_track.append(m)
        new_track.extend(track)
        if not any(m.type == "end_of_track" for m in new_track):
            new_track.append(MetaMessage("end_of_track", time=0))
        out.tracks.append(new_track)

        name = None
        for m in track:
            if m.type == "track_name":
                name = m.name
                break
        filename = f"{i:02d}_{name}.mid" if name else f"track_{i:02d}.mid"
        filename = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
        out_path = os.path.join(out_dir, filename)
        out.save(out_path)
        written.append(out_path)

    print(f"Split {input_path} into {len(written)} file(s) in {out_dir}:")
    for p in written:
        print(f"  {p}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_merge = sub.add_parser("merge")
    p_merge.add_argument("inputs", nargs="+")
    p_merge.add_argument("--out", required=True)

    p_split = sub.add_parser("split")
    p_split.add_argument("input")
    p_split.add_argument("--out-dir", required=True)

    args = parser.parse_args()
    if args.mode == "merge":
        merge(args.inputs, args.out)
    else:
        split(args.input, args.out_dir)


if __name__ == "__main__":
    main()
