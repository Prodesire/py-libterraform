#!/usr/bin/env python3
import argparse
from pathlib import Path


def normalize_wheel_tags(dist_dir, manylinux_tag="manylinux_2_35"):
    dist_path = Path(dist_dir)
    renamed = []
    for wheel in sorted(dist_path.glob("*.whl")):
        if "-linux_" not in wheel.name:
            continue
        target = wheel.with_name(wheel.name.replace("-linux_", f"-{manylinux_tag}_"))
        wheel.rename(target)
        renamed.append((wheel, target))
    return renamed


def build_parser():
    parser = argparse.ArgumentParser(
        description="Normalize platform tags for Linux wheels produced by uv build."
    )
    parser.add_argument(
        "dist_dir",
        nargs="?",
        default="dist",
        type=Path,
        help="Distribution directory containing wheel files.",
    )
    parser.add_argument(
        "--manylinux-tag",
        default="manylinux_2_35",
        help="manylinux platform tag to use when rewriting linux wheels.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    renamed = normalize_wheel_tags(args.dist_dir, manylinux_tag=args.manylinux_tag)
    for source, target in renamed:
        print(f"{source.name} -> {target.name}")
    return renamed


if __name__ == "__main__":
    main()
