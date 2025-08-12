#!/usr/bin/env python3
import argparse
import os
import sys
import json
import math
import struct
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from plyfile import PlyData

# Compact 36-byte format per splat as per provided WRITE_FORMAT
ENDIAN = "!"  # network (big-endian), matches the sample code
WRITE_FORMAT = {
    'start_frame': 'H',   # uint16
    'end_frame': 'H',     # uint16
    'xyz': 'fff',         # 3 * float32
    'color': 'BBB',       # 3 * uint8
    'opacity': 'B',       # 1 * uint8
    'scaling': 'fff',     # 3 * float32
    'rotation': 'BBBB',   # 4 * uint8 (normalized quaternion)
}

FMT_STR = f"{ENDIAN}{''.join(WRITE_FORMAT.values())}"
RECORD_SIZE = struct.calcsize(FMT_STR)


def list_ply_files(input_path: str) -> List[str]:
    if os.path.isdir(input_path):
        files = [
            os.path.join(input_path, f)
            for f in sorted(os.listdir(input_path))
            if f.lower().endswith('.ply')
        ]
        return files
    if os.path.isfile(input_path) and input_path.lower().endswith('.ply'):
        return [input_path]
    return []


def read_vertices_colors(ply_path: str) -> Tuple[np.ndarray, np.ndarray]:
    ply = PlyData.read(ply_path)
    v = ply['vertex'].data

    # xyz
    xyz = np.stack([v['x'], v['y'], v['z']], axis=1).astype(np.float32)

    # color: support red/green/blue or r/g/b, else default white
    color_fields = None
    for candidate in [("red", "green", "blue"), ("r", "g", "b")]:
        if all(name in v.dtype.names for name in candidate):
            color_fields = candidate
            break
    if color_fields is not None:
        colors = np.stack([v[color_fields[0]], v[color_fields[1]], v[color_fields[2]]], axis=1)
        # Ensure uint8
        if colors.dtype != np.uint8:
            colors = np.clip(colors, 0, 255).astype(np.uint8)
    else:
        colors = np.full((xyz.shape[0], 3), 255, dtype=np.uint8)

    return xyz, colors


def normalize_quaternion_to_bytes(q: Sequence[float]) -> Tuple[int, int, int, int]:
    # q is (w, x, y, z). Normalize and map [-1,1] -> [0,255]
    w, x, y, z = q
    length = math.sqrt(w*w + x*x + y*y + z*z)
    if length == 0:
        w, x, y, z = 1.0, 0.0, 0.0, 0.0
    else:
        w, x, y, z = w/length, x/length, y/length, z/length
    def to_byte(val: float) -> int:
        # Map [-1,1] -> [0,255]
        b = int(val * 128 + 128)
        return max(0, min(255, b))
    return to_byte(w), to_byte(x), to_byte(y), to_byte(z)


def generate_records_for_file(
    ply_path: str,
    start_frame: int,
    end_frame: int,
    default_opacity: int,
    default_scale: float,
    rotation_wxyz: Sequence[float],
) -> Iterable[Tuple]:
    xyz, colors = read_vertices_colors(ply_path)

    # Prepare per-vertex arrays
    num = xyz.shape[0]
    opacity = np.full((num,), default_opacity, dtype=np.uint8)
    scaling = np.full((num, 3), default_scale, dtype=np.float32)
    rot_bytes = normalize_quaternion_to_bytes(rotation_wxyz)

    # Pack tuples according to FMT_STR
    for i in range(num):
        x, y, z = float(xyz[i, 0]), float(xyz[i, 1]), float(xyz[i, 2])
        r, g, b = int(colors[i, 0]), int(colors[i, 1]), int(colors[i, 2])
        o = int(opacity[i])
        sx, sy, sz = float(scaling[i, 0]), float(scaling[i, 1]), float(scaling[i, 2])
        rw, rx, ry, rz = rot_bytes
        yield (
            int(start_frame),
            int(end_frame),
            x, y, z,
            r, g, b,
            o,
            sx, sy, sz,
            rw, rx, ry, rz,
        )


def write_format_json(output_path: str):
    directory = os.path.dirname(output_path) or "."
    with open(os.path.join(directory, 'format.json'), 'w') as f:
        json.dump(WRITE_FORMAT, f, indent=2)


def write_dat(records: Iterable[Tuple], output_path: str) -> int:
    write_format_json(output_path)
    count = 0
    with open(output_path, 'wb') as f:
        for rec in records:
            f.write(struct.pack(FMT_STR, *rec))
            count += 1
    return count


def validate_dat(input_path: str, head: int = 3) -> None:
    size = os.path.getsize(input_path)
    if size % RECORD_SIZE != 0:
        print(f"Warning: file size {size} is not a multiple of record size {RECORD_SIZE}")
    total = size // RECORD_SIZE
    print(f"Format: {FMT_STR} ({RECORD_SIZE} bytes/rec). Records: {total}")
    with open(input_path, 'rb') as f:
        for i in range(min(head, total)):
            data = f.read(RECORD_SIZE)
            tup = struct.unpack(FMT_STR, data)
            print(f"rec[{i}]: {tup}")


def main():
    parser = argparse.ArgumentParser(description="Convert PLY files into compact 36B .dat format for SwinGSplat/demo")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--input', type=str, help='Directory containing .ply files or a single .ply file')
    src.add_argument('--ply', type=str, nargs='+', help='One or more .ply files (absolute paths recommended)')
    parser.add_argument('--output', type=str, required=False, default='output.dat', help='Output .dat path')
    parser.add_argument('--frame-step', type=int, default=1, help='Frame increment per file (default 1)')
    parser.add_argument('--default-opacity', type=int, default=255, help='Opacity 0-255 (default 255)')
    parser.add_argument('--default-scale', type=float, default=1.0, help='Uniform XYZ scale if none provided (default 1.0)')
    parser.add_argument('--rotation', type=float, nargs=4, metavar=('w','x','y','z'), default=(1.0,0.0,0.0,0.0), help='Quaternion w x y z (default 1 0 0 0)')
    parser.add_argument('--validate', type=str, help='Validate an existing .dat: prints header and first few records')

    args = parser.parse_args()

    if args.validate:
        validate_dat(args.validate)
        return 0

    if args.ply:
        ply_files = [p for p in args.ply if os.path.isfile(p)]
    else:
        ply_files = list_ply_files(args.input)

    if not ply_files:
        print("No .ply files found.", file=sys.stderr)
        return 2

    # Build records across files, assigning frames per file
    start_frame = 0
    end_frame = 0
    frame_step = args.frame_step
    all_records_iterables: List[Iterable[Tuple]] = []
    for idx, ply_path in enumerate(ply_files):
        start_frame = idx * frame_step
        end_frame = start_frame  # treat each file as a single frame range
        recs = generate_records_for_file(
            ply_path=ply_path,
            start_frame=start_frame,
            end_frame=end_frame,
            default_opacity=args.default_opacity,
            default_scale=args.default_scale,
            rotation_wxyz=args.rotation,
        )
        all_records_iterables.append(recs)

    # Chain and write
    def chain_iters(iters):
        for it in iters:
            for x in it:
                yield x

    total = write_dat(chain_iters(all_records_iterables), args.output)
    print(f"Wrote {total} records to {args.output} ({RECORD_SIZE} bytes/record, total {total*RECORD_SIZE} bytes)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
