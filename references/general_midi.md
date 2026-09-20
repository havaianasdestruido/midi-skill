# General MIDI (GM) reference

General MIDI defines a standard mapping of `program_change` numbers (0-127) to instrument sounds, so a file plays back with roughly the right sound on any GM-compliant synth. Program numbers below are 0-indexed (as `mido` and the raw MIDI byte use them) — many books/UIs show them 1-indexed (1-128), so subtract 1 if the user quotes a number from such a source.

## Instrument families (program numbers, 0-indexed)

| Range | Family | Notable programs |
|---|---|---|
| 0-7 | Piano | 0 Acoustic Grand, 1 Bright Acoustic, 4 Electric Piano 1, 5 Electric Piano 2 |
| 8-15 | Chromatic Percussion | 8 Celesta, 9 Glockenspiel, 13 Xylophone |
| 16-23 | Organ | 16 Drawbar Organ, 19 Church Organ, 21 Accordion |
| 24-31 | Guitar | 24 Nylon, 25 Steel Acoustic, 27 Clean Electric, 29 Overdriven, 30 Distortion |
| 32-39 | Bass | 32 Acoustic Bass, 33 Fingered Electric Bass, 34 Picked Electric Bass, 38 Synth Bass 1 |
| 40-47 | Strings | 40 Violin, 41 Viola, 42 Cello, 43 Contrabass, 48 (next range) Strings Ensemble |
| 48-55 | Ensemble | 48 String Ensemble 1, 52 Choir Aahs, 53 Voice Oohs |
| 56-63 | Brass | 56 Trumpet, 57 Trombone, 58 Tuba, 61 Brass Section |
| 64-71 | Reed | 64 Soprano Sax, 65 Alto Sax, 66 Tenor Sax, 71 Clarinet |
| 72-79 | Pipe | 73 Flute, 74 Recorder, 78 Whistle |
| 80-87 | Synth Lead | 80 Square, 81 Sawtooth |
| 88-95 | Synth Pad | 88 New Age, 89 Warm, 90 Polysynth |
| 96-103 | Synth Effects | 96 Rain, 99 Atmosphere |
| 104-111 | Ethnic | 104 Sitar, 105 Banjo, 106 Shamisen, 108 Kalimba |
| 112-119 | Percussive | 112 Tinkle Bell, 114 Steel Drums, 116 Taiko, 117 Melodic Tom |
| 120-127 | Sound Effects | 120 Guitar Fret Noise, 122 Seashore, 123 Bird Tweet |

For a program not to sound wrong, always send it as a `program_change` message on the channel *before* any `note_on` on that channel — `create_midi.py` does this automatically from the `program` field in the note spec.

## Percussion key map (channel 9 only)

On channel 9 (10th channel), the pitch of a `note_on` selects a drum/percussion sound instead of a musical pitch. Standard General MIDI drum map (most commonly used):

| Note | Sound | Note | Sound |
|---|---|---|---|
| 35 | Acoustic Bass Drum | 42 | Closed Hi-Hat |
| 36 | Bass Drum 1 (kick) | 44 | Pedal Hi-Hat |
| 38 | Acoustic Snare | 46 | Open Hi-Hat |
| 40 | Electric Snare | 49 | Crash Cymbal 1 |
| 37 | Side Stick | 51 | Ride Cymbal 1 |
| 39 | Hand Clap | 56 | Cowbell |
| 41 | Low Floor Tom | 43 | High Floor Tom |
| 45 | Low Tom | 47 | Low-Mid Tom |
| 48 | Hi-Mid Tom | 50 | High Tom |
| 54 | Tambourine | 70 | Maracas |

A basic rock/pop beat pattern in 4/4 typically uses: kick (36) on beats 1 and 3, snare (38) on beats 2 and 4, closed hi-hat (42) on every 8th note.
