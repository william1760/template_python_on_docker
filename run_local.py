import os
import secrets
import subprocess
import sys


_DOCKER_SECRET_FILE = '.docker_secret'


def _ensure_keymanager_password():
    """
    Ensure KEYMANAGER_PASSWORD is set for this process session.
    Resolution order:
      1. Already set in os.environ (export / PyCharm run config) → used as-is
      2. .docker_secret exists → read from it (consistent with Docker)
      3. Neither → generate random (only safe for a fresh Token.key)
    """
    if os.environ.get('KEYMANAGER_PASSWORD'):
        return

    if os.path.exists(_DOCKER_SECRET_FILE):
        with open(_DOCKER_SECRET_FILE, 'r') as f:
            os.environ['KEYMANAGER_PASSWORD'] = f.read().strip()
        return

    password = secrets.token_hex(32)
    with open(_DOCKER_SECRET_FILE, 'w') as f:
        f.write(password)
    os.chmod(_DOCKER_SECRET_FILE, 0o600)
    os.environ['KEYMANAGER_PASSWORD'] = password


_ensure_keymanager_password()

# subprocess inherits os.environ from this process, so the env var flows through.
# cwd='src' mirrors how main.py runs inside Docker (workdir is /app/src).
result = subprocess.run(
    [sys.executable, 'main.py'] + sys.argv[1:],
    cwd='src'
)
sys.exit(result.returncode)
