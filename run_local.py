import os
import secrets
import subprocess
import sys


def _ensure_keymanager_password():
    """
    Ensure KEYMANAGER_PASSWORD is set for this process session.
    - Already set (export / PyCharm run config) → used as-is
    - Not set → generates a random one for this process lifetime only

    NOTE: A random password only works for a fresh Token.key.
          If Token.key already exists, set KEYMANAGER_PASSWORD to match it first:
              export KEYMANAGER_PASSWORD=$(cat .docker_secret)
              python run_local.py --setup
    """
    if not os.environ.get('KEYMANAGER_PASSWORD'):
        os.environ['KEYMANAGER_PASSWORD'] = secrets.token_hex(32)


_ensure_keymanager_password()

# subprocess inherits os.environ from this process, so the env var flows through.
# cwd='src' mirrors how main.py runs inside Docker (workdir is /app/src).
result = subprocess.run(
    [sys.executable, 'main.py'] + sys.argv[1:],
    cwd='src'
)
sys.exit(result.returncode)
