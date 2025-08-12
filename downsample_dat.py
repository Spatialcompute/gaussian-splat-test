#!/usr/bin/env python3
import argparse
import os
import struct

ENDIAN = '!'
FMT = f"{ENDIAN}HHfffBBBBfffBBBB"
RECORD_SIZE = struct.calcsize(FMT)


def iter_records(path, chunk_bytes=4*1024*1024):
    # ensure chunk size aligns to record size
    chunk_bytes -= (chunk_bytes % RECORD_SIZE)
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_bytes)
            if not chunk:
                break
            m = len(chunk)//RECORD_SIZE
            for i in range(m):
                start = i*RECORD_SIZE
                yield chunk[start:start+RECORD_SIZE]


def downsample(input_path: str, output_path: str, min_span: int, stride: int, limit: int | None) -> int:
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    kept = 0
    total = 0
    with open(output_path, 'wb') as out:
        for rec in iter_records(input_path):
            total += 1
            if stride > 1 and (total % stride) != 0:
                continue
            sf, ef = struct.unpack_from('!HH', rec, 0)
            if (ef - sf) < min_span:
                continue
            out.write(rec)
            kept += 1
            if limit and kept >= limit:
                break
    return kept


def main():
    p = argparse.ArgumentParser(description='Downsample compact 36B .dat to reduce ghosting and load')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--min-span', type=int, default=5, help='Keep only splats with (end-start) >= min-span (default 5)')
    p.add_argument('--stride', type=int, default=60, help='Keep every Nth record after span filter (default 60)')
    p.add_argument('--limit', type=int, default=800000, help='Stop after writing this many records (default 800k)')
    args = p.parse_args()

    kept = downsample(args.input, args.output, args.min_span, args.stride, args.limit)
    size = kept*RECORD_SIZE
    print(f'Wrote {kept} records ({size} bytes) to {args.output}')


if __name__ == '__main__':
    main()
