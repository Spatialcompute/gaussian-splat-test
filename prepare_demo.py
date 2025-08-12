#!/usr/bin/env python3
import argparse
import os
import shutil
import struct
import json

ENDIAN = "!"
STREAM_ROW_LENGTH = 36
VERTEX_ROW_LENGTH = 32
FMT_STR = f"{ENDIAN}HHfffBBBBfffBBBB"  # same total size 36, but we only use size
RECORD_SIZE = struct.calcsize(FMT_STR)

DEMO_DIR = os.path.join(os.path.dirname(__file__), 'demo')
DATA_DIR = os.path.join(DEMO_DIR, 'data')
CONFIG_PATH = os.path.join(DEMO_DIR, 'config_local.json')
MAIN_JS_PATH = os.path.join(DEMO_DIR, 'main.js')


def count_records(dat_path: str) -> int:
    size = os.path.getsize(dat_path)
    if size % RECORD_SIZE != 0:
        raise RuntimeError(f"{dat_path} size {size} is not a multiple of record size {RECORD_SIZE}")
    return size // RECORD_SIZE


def write_config(model_rel_url: str, total_cap: int, max_frame: int = 1):
    config = {
        "MODEL_URL": model_rel_url,
        "MAX_FRAME": max_frame,
        "SLICE_NUM": 1,
        "TOTAL_CAP": total_cap,
        "STREAM_ROW_LENGTH": STREAM_ROW_LENGTH,
        "SH_DEGREE": 0,
        "VERTEX_ROW_LENGTH": VERTEX_ROW_LENGTH,
        "INIT_VIEW": [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 5, 1
        ],
        "fx": 1835.0,
        "fy": 1835.0,
        "W": 1920,
        "H": 1080,
        "FPS": 30,
        "PREFETCH_SEC": 1,
    }
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def patch_main_js_for_local_config():
    with open(MAIN_JS_PATH, 'r', encoding='utf-8') as f:
        src = f.read()
    # Replace the remote URL construction with local file reference
    marker = "const params = new URLSearchParams(location.search);"
    if 'config_local.json' in src:
        return
    # Replace the assignment of target_config to forced local
    src = src.replace(
        "    let target_config = new URL(\n        `config_${target}.json`,\n        atob('aHR0cHM6Ly9odWdnaW5nZmFjZS5jby9OZXV0cmlub0xpdS90ZXN0R1MvcmF3L21haW4v'),\n    );",
        "    let target_config = 'config_local.json';",
    )
    with open(MAIN_JS_PATH, 'w', encoding='utf-8') as f:
        f.write(src)


def main():
    parser = argparse.ArgumentParser(description='Prepare the local demo to load a generated .dat')
    parser.add_argument('--dat', required=True, help='Path to the .dat file to serve in the demo')
    parser.add_argument('--name', default='model.dat', help='Destination filename inside demo/data (default model.dat)')
    parser.add_argument('--max-frame', type=int, default=1, help='MAX_FRAME to write into config (default 1)')
    args = parser.parse_args()

    src = os.path.abspath(args.dat)
    if not os.path.isfile(src):
        raise FileNotFoundError(src)

    os.makedirs(DATA_DIR, exist_ok=True)
    dst = os.path.join(DATA_DIR, args.name)
    shutil.copy2(src, dst)

    total = count_records(dst)
    write_config(model_rel_url=f"data/{args.name}", total_cap=total, max_frame=args.max_frame)
    patch_main_js_for_local_config()

    print(f"Prepared demo: {dst} ({total} records). Config: {CONFIG_PATH}")


if __name__ == '__main__':
    main()
