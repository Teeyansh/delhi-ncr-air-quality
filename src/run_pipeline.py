"""Run the pipeline steps in order.

    python src/run_pipeline.py                # everything (needs OpenAQ + Copernicus credentials)
    python src/run_pipeline.py --skip-fetch   # steps 03-10, if data/ already holds the downloads
    python src/run_pipeline.py --from-step 7  # resume from step 7 (features -> model -> plots)
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = sorted(p.name for p in HERE.glob("[0-9][0-9]_*.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--skip-fetch", action="store_true", help="skip steps 01-02 (API downloads)")
    parser.add_argument("--from-step", type=int, default=1, help="first step number to run")
    args = parser.parse_args()

    first = 3 if args.skip_fetch else 1
    steps = [s for s in STEPS if int(s[:2]) >= max(first, args.from_step)]

    for step in steps:
        print(f"\n{'=' * 60}\n>>> {step}\n{'=' * 60}", flush=True)
        subprocess.run([sys.executable, str(HERE / step)], check=True)
    print("\nPipeline finished. Start the dashboard with:  streamlit run app/dashboard.py")


if __name__ == "__main__":
    main()
