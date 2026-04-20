#!/usr/bin/env python3
"""Clarity — voice analysis CLI."""

import argparse
import sys
from pathlib import Path

from core.analysis import analyze_array
from core.recorder import record, load_file
from core.report import text_summary, pitch_contour_figure, save_figure


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="clarity",
        description="Clarity: acoustic voice analysis",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", metavar="PATH", help="Audio file to analyze (WAV or MP3)")
    source.add_argument(
        "--record", metavar="SECONDS", type=float, help="Record from microphone for N seconds"
    )

    parser.add_argument("--plot", metavar="PATH", help="Save pitch contour plot (PNG)")
    parser.add_argument("--out", metavar="PATH", help="Save text report to file")

    args = parser.parse_args()

    if args.file:
        print(f"Loading {args.file} ...")
        audio, sr = load_file(args.file)
    else:
        print(f"Recording for {args.record}s — speak now ...")
        audio, sr = record(args.record)
        print("Done.")

    print("Analyzing ...")
    result = analyze_array(audio, sr)

    report = text_summary(result)
    print(report)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report saved to {args.out}")

    if args.plot:
        fig = pitch_contour_figure(result)
        save_figure(fig, args.plot)
        print(f"Plot saved to {args.plot}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
