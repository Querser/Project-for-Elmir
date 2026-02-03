# backend/tools/check_unpaid_and_autoban.py
import sys
import time
import argparse

sys.path.append("/app")

from app.services.enrollment_service import check_unpaid_enrollments_and_autoban


def run_once() -> None:
    check_unpaid_enrollments_and_autoban()
    print("✅ check_unpaid_enrollments_and_autoban: done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run unpaid enrollments check and autoban job.")
    parser.add_argument("--loop", action="store_true", help="Run in loop")
    parser.add_argument("--interval", type=int, default=60, help="Interval seconds for --loop")
    args = parser.parse_args()

    if not args.loop:
        run_once()
        return

    print(f"🔁 Loop mode enabled. Interval: {args.interval}s")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"❌ Job failed: {e}")
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()