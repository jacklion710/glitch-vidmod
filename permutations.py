"""
Generate parameter permutations for datamosh-style corruption and render outputs.

Usage:
  python permutations.py 20
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List


def halton_value(index: int, base: int) -> float:
    """Return Halton sequence value in [0, 1) for a given base."""
    result = 0.0
    f = 1.0
    i = index
    while i > 0:
        f /= base
        result += f * (i % base)
        i //= base
    return result


def scale_int(value: float, low: int, high: int) -> int:
    """Scale [0, 1) to inclusive integer range [low, high]."""
    if low == high:
        return low
    return low + int(value * (high - low + 1))


def build_ffmpeg_command(input_path: str, output_path: str, params: Dict[str, int]) -> List[str]:
    # Runtime: O(1)
    # Note: -x264-params uses ':' as its delimiter, so values that contain ':' (like deblock a:b)
    # must escape the colon as '\:' or the params string becomes invalid.
    deblock_a = params["deblock"]
    deblock_b = params["deblock"]
    deblock_param = f"deblock={deblock_a}\\:{deblock_b}"
    x264_params = (
        f"keyint={params['keyint']}:"
        f"keyint_min={params['keyint_min']}:"
        f"scenecut={params['scenecut']}:"
        f"bframes={params['bframes']}:"
        f"ref={params['ref']}:"
        f"open-gop={params['open_gop']}:"
        f"{deblock_param}"
    )
    noise_filter = f"noise=amount={params['noise']}*not(key)"

    return [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-x264-params",
        x264_params,
        "-crf",
        str(params["crf"]),
        "-bsf:v",
        noise_filter,
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate datamosh parameter permutations.")
    parser.add_argument("count", type=int, help="Number of permutations to render")
    args = parser.parse_args()

    if args.count <= 0:
        print("count must be a positive integer", file=sys.stderr)
        return 1

    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "vids", "bball.mov")
    out_dir = os.path.join(script_dir, "permutations")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(input_path):
        print(f"Input video not found: {input_path}", file=sys.stderr)
        return 1

    # Reasonable ranges for exploration (adjust to taste).
    ranges = {
        "keyint": (5, 80),
        "scenecut": (0, 40),
        "bframes": (0, 8),
        "ref": (1, 6),
        "open_gop": (0, 1),
        "crf": (16, 32),
        "deblock": (-4, 4),
        "noise": (1000, 8000),
    }

    params_log: List[Dict[str, int]] = []
    primes = [2, 3, 5, 7, 11, 13, 17, 19]

    for idx in range(1, args.count + 1):
        # Low-discrepancy sampling for uniform coverage.
        keyint = scale_int(halton_value(idx, primes[0]), *ranges["keyint"])
        keyint_min = scale_int(halton_value(idx, primes[1]), 1, keyint)

        params = {
            "keyint": keyint,
            "keyint_min": keyint_min,
            "scenecut": scale_int(halton_value(idx, primes[2]), *ranges["scenecut"]),
            "bframes": scale_int(halton_value(idx, primes[3]), *ranges["bframes"]),
            "ref": scale_int(halton_value(idx, primes[4]), *ranges["ref"]),
            "open_gop": scale_int(halton_value(idx, primes[5]), *ranges["open_gop"]),
            "crf": scale_int(halton_value(idx, primes[6]), *ranges["crf"]),
            "deblock": scale_int(halton_value(idx, primes[7]), *ranges["deblock"]),
            "noise": scale_int(halton_value(idx, 23), *ranges["noise"]),
        }

        output_name = f"bball_perm_{idx:03d}.mp4"
        output_path = os.path.join(out_dir, output_name)
        cmd = build_ffmpeg_command(input_path, output_path, params)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ffmpeg failed on permutation {idx}:\n{result.stderr}", file=sys.stderr)
            return 1

        record = {"index": idx, "output": output_name}
        record.update(params)
        params_log.append(record)

    params_path = os.path.join(out_dir, "params.json")
    with open(params_path, "w", encoding="utf-8") as handle:
        json.dump(params_log, handle, indent=2)

    print(f"Generated {args.count} permutations in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
