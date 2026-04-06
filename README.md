
# Template for Python projects that runs as a Docker image

A Python-based application for task scheduling, configuration management, and Telegram notifications, packaged as a Docker image.

---

## Usage

## 1. Update `DockerCtrl.config` file
```bash
docker_image="template_python_on_docker"
image_tag="latest"
bash_type="SH"
restart_policy="UNLESS_STOPPED"
setup="python main.py --setup"
docker_secret=".docker_secret"
```

### Fields:
- `docker_image`: Name of the Docker image to be used.
- `image_tag`: Tag for the Docker image (e.g., "latest").
- `bash_type`: Type of shell to be used (`SH` or `BASH`).
- `restart_policy`: Docker container restart policy (`UNLESS_STOPPED`, `ALWAYS`, etc.).
- `setup`: The command to set up the application inside the container.
- `docker_secret`: Path to the master password file injected into the container as `KEYMANAGER_PASSWORD`.

---

## 2. Update `config.json` file and located in the `/src` directory

   ```json
   {
   "title": "template_python_on_docker",
   "log_file_name": "template_python_on_docker",
   "interval": 1,
   "schedule": "",
   "schedule_misfire_grace_time": 300,
   "notification": "a",
   "checkpoint_notification": "y",
   "telegram": "TG_TESTING"
   }
   ```

### Fields:
   - `title`: The title of the application.
   - `log_file_name`: The name of the log file.
   - `interval`: Interval in minutes for tasks (0 = disabled).
   - `schedule`: Scheduled time in HH:MM format (empty string = disabled).
   - `schedule_misfire_grace_time`: Grace time for missed schedules (seconds).
   - `notification`: Enable notifications — `y` (yes), `n` (no), `a` (always, including checkpoints).
   - `checkpoint_notification`: Send a notification at each scheduler checkpoint (`y`/`n`).
   - `telegram`: Telegram chatroom identifier.

---

## 3. Running locally with `run_local.py`

`run_local.py` is the local development launcher. It mirrors how Docker runs `main.py` by ensuring the `KEYMANAGER_PASSWORD` environment variable is set before spawning `main.py` as a subprocess with `cwd=src`.

### Password resolution order:
1. `KEYMANAGER_PASSWORD` already set in environment (e.g. PyCharm run config) → used as-is
2. `.docker_secret` exists → read from it (stays consistent with Docker)
3. Neither present → generate a random password, write it to `.docker_secret` (safe only for a fresh `Token.key`)

### Usage:
```bash
# Interactive setup (create/update credentials and config)
python run_local.py --setup

# Run main logic once immediately
python run_local.py --run

# Run scheduler loop (default)
python run_local.py
```

> **Note:** `.docker_secret` is gitignored and chmod 600. It is the single source of truth for the master password shared between local dev and Docker. If it is regenerated, `Token.key` must be re-created via `--setup`.
