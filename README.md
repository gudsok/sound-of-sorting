# Sound of Sorting

Sound of Sorting is an interactive visualizer that animates common sorting algorithms while producing short tones for array operations — a playful way to both see and hear how sorting works.

The project is implemented in Python using Pygame for graphics and audio and NumPy for efficient numeric work.

## Features

- Real-time visualization of array bars for each algorithm
- Short audio tones mapped to element values so you can "hear" comparisons and swaps
- Included algorithms: Bubble, Selection, Insertion, Merge, Quick, Heap
- Keyboard controls for selecting algorithms, shuffling, pausing, and speed control

## Requirements

- Python 3.8+
- See `requirements.txt` (pygame, numpy)

## Install

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Start the visualizer with:

```bash
python sorting_visualizer.py
```

The window will open and you can control the visualizer with the keyboard (see Controls below).

## Controls

- 1 — Bubble Sort
- 2 — Selection Sort
- 3 — Insertion Sort
- 4 — Merge Sort
- 5 — Quick Sort
- 6 — Heap Sort
- R — Shuffle the array
- SPACE — Pause / Resume (while a sort is running)
- + / = — Speed up (decrease delay)
- - — Slow down (increase delay)
- Q / Esc — Quit

## Project layout

- `sorting_visualizer.py` — main visualizer and algorithm implementations
- `requirements.txt` — Python dependencies
- `README.md` — this file

## Notes for contributors

- The sorting algorithms are implemented as step-by-step generators that call a shared `_step` helper to handle highlights, sound, and timing. That makes it straightforward to add or modify algorithms while preserving the visual/audio behaviour.
- Keep audio generation lightweight — tones are cached to avoid GC pressure during fast sorts.

## License

This repository includes a `LICENSE` file. By default use the terms described there.

## Acknowledgements

Inspired by algorithm visualizers and sonification projects that make algorithms more tangible by combining sight and sound.

Enjoy exploring sorting algorithms — both visually and aurally!
# sound-of-sorting