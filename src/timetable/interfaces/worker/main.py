import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("timetable.worker")


def main() -> None:
    """Worker tạm: chạy lên, ghi log, chờ. Sẽ nối SolveTimetable ở Ngày 6."""
    logger.info("Worker started. JOB_ID=%s", os.getenv("JOB_ID", "<none>"))
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
