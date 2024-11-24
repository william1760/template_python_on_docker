
# Template Python Project with Docker

A Python-based application designed for task scheduling, configuration management, and Telegram notifications, packaged for use with Docker.

---

## Usage

1. Update `DockerCtrl.config` file
    ```bash
    docker_image="template_python_on_docker"
    image_tag="latest"
    bash_type="SH"
    restart_policy="UNLESS_STOPPED"
    setup="python main.py --setup"
     ```

2. Update `config.json` file and located in the `/src` directory

   ```json
   {
   "title": "template_python_on_docker",
   "log_file_name": "template_python_on_docker",
   "interval": 0,
   "schedule": "14:28",
   "schedule_misfire_grace_time": 300,
   "notification": "y",
   "telegram": "TESTING"
   }
   ```

   Fields:
   - `title`: The title of the application.
   - `log_file_name`: The name of the log file.
   - `interval`: Interval in minutes for tasks.
   - `schedule`: Scheduled time (HH:MM format).
   - `schedule_misfire_grace_time`: Grace time for missed schedules (seconds).
   - `notification`: Enable notifications (`y`/`n`).
   - `telegram`: Telegram chatroom identifier.
