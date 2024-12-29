import sys
import logging
from io import StringIO
from contextlib import redirect_stdout
from tzlocal import get_localzone
from apscheduler.schedulers.blocking import BlockingScheduler
from TimeToolkit import TimeToolkit


class Scheduler:
    def __init__(self):
        self.scheduler = BlockingScheduler(timezone=str(get_localzone()))

    def show_jobs(self):
        print("show_jobs")

        """Display all scheduled jobs."""
        if not self.scheduler.get_jobs():
            print("[Scheduler.show_jobs] No jobs currently scheduled.")
            logging.info("[Scheduler.show_jobs] No jobs currently scheduled.")
        else:
            with StringIO() as buffer:
                with redirect_stdout(buffer):
                    self.scheduler.print_jobs()  # Print jobs to buffer
                jobs_output = buffer.getvalue().strip()

            print("[Scheduler.show_jobs] Current jobs:")
            print(jobs_output)
            logging.info(f"[Scheduler.show_jobs] Current jobs:\n{jobs_output}")

    def add(self,
            input_main,
            schedule_type: str = 'interval',
            interval: int = 0,
            checkpoint_notification: bool = False,
            schedule_time: str = None,
            misfire_grace_time: int = 300) -> None:
        # Validate the schedule type
        if schedule_type.lower() not in ['interval', 'cron']:
            raise KeyError(f"[Scheduler.add] Invalid schedule_type (allowed: 'interval' / 'cron'): {schedule_type}")

        # Parse schedule time if provided
        schedule_time = TimeToolkit.parse_time_string(schedule_time) if schedule_time else None
        extra_args = {"trigger_notification": True} if checkpoint_notification else None
        schedule_message = ""
        job_id = ""

        # Add job based on schedule type
        if schedule_type.lower() == 'cron':
            job_id = f"cron_task_{schedule_time[0]}_{schedule_time[1]}"
            schedule_message = f"Time={schedule_time[0]}:{schedule_time[1]}, misfire_grace_time={misfire_grace_time}"
            if not schedule_time:
                raise ValueError("schedule_time must be provided for 'cron' jobs.")
            self.scheduler.add_job(
                input_main,
                trigger=schedule_type,
                hour=schedule_time[0],
                minute=schedule_time[1],
                misfire_grace_time=misfire_grace_time,
                id=job_id,
                kwargs=extra_args
            )
        elif schedule_type.lower() == 'interval':
            job_id = f"interval_task_{interval}"
            schedule_message = f"Minutes={interval}, misfire_grace_time={misfire_grace_time}"
            if interval == 0:
                raise ValueError("interval must be a positive integer for 'interval' jobs.")
            self.scheduler.add_job(
                input_main,
                trigger=schedule_type,
                minutes=interval,
                misfire_grace_time=misfire_grace_time,
                id=job_id,
                kwargs=extra_args
            )

        # Log the added job details
        logging.info(f"[Scheduler.add] Added job: ID={job_id}, Trigger={schedule_type}, {schedule_message}")

    def start(self):
        """Start the scheduler."""
        try:
            print("[Scheduler.start] Starting the scheduler...")
            logging.info("[Scheduler.start] Scheduler is starting...")
            self.scheduler.start()
        except KeyboardInterrupt:
            print("[Scheduler.start] Scheduler stopped by user (Ctrl+C).")
            logging.warning("Scheduler stopped by user (Ctrl+C).")
        except Exception as e:
            print(f"[Scheduler.start] Scheduler stopped due to an unexpected error: {e}")
            logging.error(f"Scheduler stopped due to an unexpected error: {e}")
            sys.exit(1)  # Exit with a failure code for unexpected errors


if __name__ == "__main__":
    Task = Scheduler()

    def demo():
        from datetime import datetime
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Function "demo" called')

    Task.add(
        demo,
        schedule_type='interval',
        interval=1,
        misfire_grace_time=300
    )

    Task.add(
        demo,
        schedule_type='cron',
        schedule_time="08:00",
        misfire_grace_time=300
    )

    Task.show_jobs()
    Task.start()
