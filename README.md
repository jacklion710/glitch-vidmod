# glitch-vidmod

Batch “corrupt” videos with FFmpeg, preview results side-by-side, and iterate on parameters with a small GUI.

## Project layout

- `vids/`: **source/original** videos (never modified by the GUI)
- `out/`: generated `*_corrupted.mp4` outputs (safe to delete/regenerate)
- `interface.py`: parameter GUI + single-video preview + batch processing
- `view.py`: side-by-side viewer (original vs corrupted)
- `mod.py`: simple batch script (no GUI)

## Requirements

- **Python**: 3.10+ recommended
- **FFmpeg**: available on your `PATH` as `ffmpeg`
- **Python packages**:
  - `opencv-python`
  - `numpy`

Install packages (example):

```bash
pip install opencv-python numpy
```

## Quick start (recommended)

1) Put videos into `vids/`.

2) Launch the GUI:

```bash
python interface.py
```

3) In the GUI:

- Pick a video from the dropdown
- Adjust parameters
- Click **Preview on Selected Video**
- The viewer will open (if “Auto-open viewer after preview” is enabled)
- When happy, click **Process All Videos (Overwrite Existing)** to regenerate everything in `out/`

## Viewer (side-by-side)

Run directly:

```bash
python view.py
```

Start on a specific video:

```bash
python view.py --video bball.mov
```

Controls:

- **A/D**: previous/next video pair
- **Space**: play/pause
- **Q** or **Esc**: quit

## Batch script (no GUI)

```bash
python mod.py
```

This loops over videos in `vids/` and writes corrupted outputs into `out/`.

## Safety note

The GUI uses absolute paths and explicitly refuses to write anywhere except `out/`.
If you ever see outputs appearing outside `out/`, you’re likely running a script from a different working directory—run from the repo folder or use `interface.py`.
