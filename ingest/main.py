from __future__ import annotations

import time


def main() -> int:
    print(
        "MarketCore ingest scaffold running; live ingest is not implemented yet.",
        flush=True,
    )

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
