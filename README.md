# TDA7429 Breakout Board & Arduino Library

Breakout board and Arduino library for the ST TDA7429 digitally controlled audio processor with surround sound matrix.

## What is the TDA7429?

The TDA7429 is an I²C-controlled audio DSP designed for TV and Hi-Fi systems. It handles input selection, volume/tone control, surround sound processing, and speaker balance — all through a two-wire serial bus with no external microcontroller overhead beyond simple register writes.

**Key specs:**
- 3 stereo inputs with 0–31.5 dB attenuation (0.5 dB steps)
- Bass, middle, and treble control (±14 dB, 2 dB steps)
- 4 independent speaker attenuators (0–79 dB, 1 dB steps + mute)
- 3 surround modes: music, movie, simulated (256 selectable responses)
- 4 programmable phase shifters
- Monitor and auxiliary outputs
- 106 dB signal-to-noise ratio
- 7–10.2 V supply

## Repository Structure

```
├── hardware/
│   ├── kicad/                  # KiCad 7+ project files
│   │   ├── TDA7429_BREAKOUT.kicad_pro
│   │   ├── TDA7429_BREAKOUT.kicad_sch
│   │   └── TDA7429_BREAKOUT.kicad_pcb
│   ├── lib/                    # KiCad symbol & footprint library
│   │   ├── TDA7429.kicad_sym
│   │   └── TDA7429.pretty/
│   │       └── SDIP-42_W15.24mm_P1.778mm.kicad_mod
│   └── eagle/                  # Original Eagle 6.5 files (reference)
│       ├── TDA7429_BREAKOUT.sch
│       └── TDA7429_BREAKOUT.brd
├── firmware/
│   └── TDA7429/                # Arduino library
│       ├── src/
│       │   ├── TDA7429.h
│       │   └── TDA7429.cpp
│       ├── examples/
│       │   └── BasicControl/
│       │       └── BasicControl.ino
│       ├── library.properties
│       └── keywords.txt
├── docs/
│   └── TDA7429S_TDA7429T.pdf   # Datasheet
└── README.md
```

## Hardware

### Breakout Board

~50 × 50 mm board carrying the TDA7429S (SDIP-42) with all external filter components from the datasheet reference circuit. Pin headers break out:

| Header     | Pins                                      |
|------------|-------------------------------------------|
| AUDIO_IN   | 3 stereo input pairs (L/R × IN1–IN3)     |
| AUDIO_OUT  | L_OUT, R_OUT, AUXOUT_L, AUXOUT_R          |
| MONITOR    | MONITOR_L, MONITOR_R                      |
| DATA       | SDA, SCL                                  |
| POWER      | +9V, GND                                  |

### Connecting to Arduino

| Breakout | Arduino Uno/Nano | Arduino Mega |
|----------|------------------|--------------|
| SDA      | A4               | 20           |
| SCL      | A5               | 21           |
| GND      | GND              | GND          |

The TDA7429 runs at 7–10.2 V — do **not** power it from the Arduino 5V pin. Use a separate 9V supply for the breakout board. The I²C bus needs pull-up resistors to the Arduino's 3.3V or 5V (4.7kΩ typical). The chip's I²C thresholds (V_IL max 1V, V_IH min 3V) are compatible with both 3.3V and 5V logic.

## Arduino Library

### Installation

Copy the `firmware/TDA7429/` folder into your Arduino libraries directory, or use the Arduino IDE Library Manager if published.

### Quick Start

```cpp
#include <Wire.h>
#include <TDA7429.h>

TDA7429 audio;

void setup() {
  Wire.begin();
  audio.begin();

  audio.selectInput(1);          // Input 1
  audio.setInputAttenuation(0);  // 0 dB (no attenuation)
  audio.setBass(0);              // Flat
  audio.setMiddle(0);            // Flat
  audio.setTreble(0);            // Flat
  audio.setSpeakerAttenuation(TDA7429_LEFT, -20);   // -20 dB
  audio.setSpeakerAttenuation(TDA7429_RIGHT, -20);  // -20 dB
  audio.setSurroundMode(TDA7429_SURROUND_OFF);
}

void loop() {
  // Adjust volume, tone, etc. from serial commands, buttons, encoder...
}
```

### API Reference

| Method | Description |
|--------|-------------|
| `begin()` | Initialize with default (muted) state |
| `selectInput(1–4)` | Choose stereo input pair |
| `setInputAttenuation(dB)` | 0 to -31.5 dB in 0.5 dB steps |
| `setBass(dB)` | -14 to +14 dB in 2 dB steps |
| `setMiddle(dB)` | -14 to +14 dB in 2 dB steps |
| `setTreble(dB)` | -14 to +14 dB in 2 dB steps |
| `setSpeakerAttenuation(ch, dB)` | 0 to -79 dB per channel, 1 dB steps |
| `setAuxAttenuation(ch, dB)` | 0 to -79 dB per channel, 1 dB steps |
| `setSurroundMode(mode)` | OFF, MUSIC, MOVIE, SIMULATED |
| `setEffectControl(dB)` | -6 to -21 dB surround effect level |
| `setPhaseShifters(...)` | Configure 4 phase shift resistors |
| `mute()` / `unmute()` | Mute/unmute all speaker outputs |

## Known Issues / TODO

- [ ] DIG_GND (pin 28) needs to be connected to ground in the schematic
- [ ] Audio connector ground pins (L-, R-) need explicit connection to AGND
- [ ] Consider adding bottom ground pour for improved noise performance
- [ ] Add ferrite bead between DIG_GND and AGND for digital/analog isolation

## License

Hardware design files are released under [CERN-OHL-P v2](https://ohwr.org/cern_ohl_p_v2.txt). Arduino library is released under the MIT License. See individual directories for details.

## Credits

Board design by Allen Kreager. Originally designed in Eagle 6.5, converted to KiCad 7.
