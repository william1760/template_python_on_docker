import sys
import logging
import time
from tzlocal import get_localzone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from .TimeToolkit import TimeToolkit


class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone=str(get_localzone()),
            job_defaults={"coalesce": False, "max_instances": 1}
        )
        self.scheduler.add_listener(self.__job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

    def __job_listener(self, event):
        """Handle job events and log details."""
        job = self.scheduler.get_job(event.job_id)  # Use self.scheduler to get the job
        if not job:
            logging.error(f"[Scheduler.job_listener] Job not found for ID: {event.job_id}")
            return

        # Centralized details
        trigger_details = str(job.trigger)
        next_run_time = getattr(job, 'next_run_time', None)
        next_run_time_str = next_run_time.strftime('%Y-%m-%d %H:%M:%S') if next_run_time else "Not Scheduled"
        event_job_details = f"ID={event.job_id}, Trigger={trigger_details}, Next Run={next_run_time_str}"

        if event.exception:
            logging.error(f"[Scheduler.job_listener] Job failed: {event_job_details}")
        elif event.code == EVENT_JOB_EXECUTED:
            event_job_executed_message = f"[Scheduler.job_listener] Job executed: {event_job_details}"
            logging.info(event_job_executed_message)
            print(event_job_executed_message)
        elif event.code == EVENT_JOB_MISSED:
            logging.warning(f"[Scheduler.job_listener] Job missed: {event_job_details}")

    def show_jobs(self):
        """Display all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            print("[Scheduler.show_jobs] No jobs currently scheduled.")
            logging.info("[Scheduler.show_jobs] No jobs currently scheduled.")
        else:
            for job in jobs:
                next_run = getattr(job, 'next_run_time', None)
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else "Not Scheduled"
                print(f"[Scheduler.show_jobs] Job ID: {job.id}, Trigger: {job.trigger}, Next Run Time: {next_run_str}")
                logging.info(
                    f"[Scheduler.show_jobs] Job ID: {job.id}, Trigger: {job.trigger}, Next Run Time: {next_run_str}"
                )

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
        except Exception as e:
            print(f"[Scheduler.start] Scheduler stopped due to an unexpected error: {e}")
            logging.error(f"[Scheduler.start] Scheduler stopped due to an unexpected error: {e}")
            sys.exit(1)  # Exit with a failure code for unexpected errors

    def shutdown(self):
        print("[Scheduler.shutdown] Shutting down the scheduler...")
        logging.info("[Scheduler.shutdown] Scheduler is Shutting down...")
        self.scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,  # Set default logging level to INFO
        format="%(asctime)s - %(levelname)s - %(message)s")
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
        schedule_time="13:16",
        misfire_grace_time=300
    )

    Task.show_jobs()
    Task.start()

    try:
        # Keep the script running
        logging.info("Scheduler is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)  # Sleep to reduce CPU usage
    except (KeyboardInterrupt, SystemExit):
        # Graceful shutdown on user interrupt
        logging.info("Stopping the scheduler...")
        Task.shutdown()
        logging.info("Scheduler stopped.")

