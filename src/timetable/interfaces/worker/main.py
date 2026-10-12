import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("timetable.worker")


def main() -> None:
    """Worker tạm. Có JOB_ID: ghi log rồi thoát. Không có: chờ (dùng cho compose).

    Sẽ nối SolveTimetable ở Ngày 6.
    """
    job_id = os.getenv("JOB_ID")
    logger.info("Worker started. JOB_ID=%s", job_id or "<none>")
    if job_id:
        logger.info("Job %s: chưa nối SolveTimetable, thoát.", job_id)
        return
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
