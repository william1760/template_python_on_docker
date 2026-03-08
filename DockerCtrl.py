import os
import secrets
import docker
import subprocess
import argparse
from docker import errors
from enum import Enum


# Color coding
text_color_red = '\033[31m'
text_color_green = '\033[32m'
text_color_yellow = '\033[33m'
text_color_white = '\033[37m'
text_color_blue = '\033[34m'
text_color_reset = '\033[0m'
text_color_purple = '\033[35m'
text_color_pink = '\033[95m'


class RestartPolicy(Enum):
    NO = "no"
    ON_FAILURE = "on-failure"
    ALWAYS = "always"
    UNLESS_STOPPED = "unless-stopped"


class BashStyle(Enum):
    BASH = "/bin/bash"
    SH = "/bin/sh"
    DASH = "/bin/dash"
    KSH = "/bin/ksh"
    ZSH = "/bin/zsh"
    CSH = "/bin/csh"
    TCSH = "/bin/tcsh"
    FISH = "/bin/fish"


class InteractMode(Enum):
    SPAWNING = "run"
    ATTACHING = "exec"
    START = "start"


class DockerCtrl:
    def __init__(self, config_file: str = 'DockerCtrl.config'):
        self.docker_image: str = ''
        self.github_url: str = ''
        self.image_tag: str = ''
        self.bash_type: str = ''
        self.restart_policy: str = ''
        self.setup: str = ''
        self.secret_file: str = '.docker_secret'
        self.client = docker.from_env()
        self._load_config(config_file)

    def _load_config(self, config_file: str):
        bash_type = None
        restart_policy_type = None

        print(f'{text_color_white}[read_config]{text_color_reset} Reading configuration from file - '
              f'\'{text_color_green}{config_file}{text_color_reset}\'')

        try:
            with open(config_file, 'r') as file:
                config_content = file.read()
        except Exception as e:
            print(f'Read config file error: {e}')
            exit(1)

        lines = config_content.split('\n')
        for line in lines:
            if line.startswith('%') or not line.strip():
                continue

            parts = line.split('=', 1)
            if len(parts) != 2:
                continue
            key, value = map(str.strip, parts)

            if key == 'docker_image':
                self.docker_image = value.strip('"')
            elif key == 'github_url':
                self.github_url = value.strip('"')
            elif key == 'image_tag':
                self.image_tag = value.strip('"')
            elif key == 'bash_type':
                bash_type = value.strip('"')
            elif key == 'setup':
                self.setup = value.strip('"')
            elif key == 'restart_policy':
                restart_policy_type = value.strip('"')
            elif key == 'docker_secret':
                self.secret_file = value.strip('"')

        for enum_member in BashStyle:
            if enum_member.name == bash_type:
                self.bash_type = enum_member.value
                break

        for enum_member in RestartPolicy:
            if enum_member.name == restart_policy_type:
                self.restart_policy = enum_member.value
                break

        print(f'{text_color_white}[read_config]{text_color_reset} Variable: '
              f'docker_image = \'{text_color_blue}{self.docker_image}{text_color_reset}\' | '
              f'github_url = \'{text_color_blue}{self.github_url}{text_color_reset}\' | '
              f'image_tag = \'{text_color_blue}{self.image_tag}{text_color_reset}\' | '
              f'restart_policy = \'{text_color_blue}{restart_policy_type}{text_color_reset}\' | '
              f'bash_type = \'{text_color_blue}{self.bash_type}{text_color_reset}\' | '
              f'setup = \'{text_color_blue}{self.setup}{text_color_reset}\' | '
              f'docker_secret = \'{text_color_blue}{self.secret_file}{text_color_reset}\'')

    def _read_master_password(self) -> str:
        """Read the master password from the host-side secret file."""
        if not os.path.exists(self.secret_file):
            print(f'{text_color_red}[docker_ctrl]{text_color_reset} '
                  f'\'{self.secret_file}\' not found. Run --build first.')
            exit(1)
        with open(self.secret_file, 'r') as f:
            return f.read().strip()

    def _image_exist(self):
        try:
            image = self.client.images.get(f'{self.docker_image}:{self.image_tag}')
        except docker.errors.ImageNotFound:
            return None
        return image

    def _container_exist(self):
        try:
            container = self.client.containers.get(self.docker_image)
        except docker.errors.NotFound:
            return None
        return container

    def stop(self):
        if self._image_exist() is not None:
            container = self._container_exist()

            if container is not None:
                if container.status == 'running':
                    print(f'{text_color_white}[docker_stop]{text_color_reset} '
                          f'Stopping container \'{text_color_blue}{container.name}{text_color_reset}\' '
                          f'(CONTAINER ID: {text_color_yellow}{container.short_id}{text_color_reset})...')

                    container.stop()
                    container.reload()

                    print(f'{text_color_white}[docker_stop]{text_color_reset} '
                          f'Container \'{text_color_blue}{container.name}{text_color_reset}\' '
                          f'status: {text_color_yellow}{container.status}{text_color_reset}')

                    return False if container.status == 'running' else True
                else:
                    print(f"{text_color_white}[docker_stop]{text_color_reset} "
                          f"Container \'{text_color_blue}{container.name}{text_color_reset}\' "
                          f"is currently {text_color_red}stopped{text_color_reset}.")
                    return True
            else:
                print(f"{text_color_white}[docker_stop]{text_color_reset} "
                      f"Error: Container \'{text_color_blue}{self.docker_image}{text_color_reset}\' not found")
                return False
        else:
            print(f'{text_color_white}[docker_stop]{text_color_reset} '
                  f'The image \'{text_color_red}{self.docker_image}:{self.image_tag}{text_color_reset}\' does not exist.')
            return False

    def remove(self):
        if self._image_exist() is not None:
            try:
                self.stop()

                container = self._container_exist()
                if container is not None:
                    print(f'{text_color_white}[docker_remove]{text_color_reset} '
                          f'Removing docker container: \'{text_color_blue}{self.docker_image}{text_color_reset}\'...')
                    container.remove(force=True)

                print(f'{text_color_white}[docker_remove]{text_color_reset} '
                      f'Removing docker image: \'{text_color_blue}{self.docker_image}{text_color_reset}\'...')
                self.client.images.remove(self.docker_image, force=True)
            except docker.errors.APIError:
                print(f'{text_color_white}[docker_remove]{text_color_reset} '
                      f'Error occurred while remove the image & container \'{text_color_blue}{self.docker_image}{text_color_reset}\'.')
        else:
            print(f'{text_color_white}[docker_remove]{text_color_reset} '
                  f'The image \'{text_color_red}{self.docker_image}:{self.image_tag}{text_color_reset}\' does not exist.')

    def build(self):
        self.remove()

        try:
            print(f'{text_color_white}[docker_build]{text_color_reset} '
                  f'Building Docker image \'{self.docker_image}\'...')

            subprocess.run(['docker', 'build', '--build-arg', f'FOLDER_NAME={self.docker_image}',
                            '-t', f'{self.docker_image}:{self.image_tag}', '.'], check=True)

            image_id = self.client.images.get(self.docker_image).short_id

            if image_id:
                print(f'{text_color_white}[docker_build]{text_color_reset} '
                      f'Docker image  \'{text_color_blue}{self.docker_image}{text_color_reset}\' '
                      f'built successfully (IMAGE ID: {text_color_yellow}{image_id}{text_color_reset}).')

                # Generate a new master password and save to host-side secret file.
                # This replaces the previous password — run --setup after every --build.
                master_password = secrets.token_hex(32)
                with open(self.secret_file, 'w') as f:
                    f.write(master_password)
                os.chmod(self.secret_file, 0o600)
                print(f'{text_color_white}[docker_build]{text_color_reset} '
                      f'Master password generated and saved to '
                      f'\'{text_color_yellow}{self.secret_file}{text_color_reset}\'. '
                      f'Run {text_color_green}--setup{text_color_reset} next.')
        except subprocess.CalledProcessError as e:
            print(f'{text_color_white}[docker_build]{text_color_reset} Build failed: {e}')
        except Exception as e:
            print(f'{text_color_white}[docker_build]{text_color_reset} Build failed: {e}')

    def _interactive_session(self, mode: InteractMode, cmd: str = ''):
        exec_cmd = cmd if cmd else self.bash_type
        if mode == InteractMode.SPAWNING:
            command = f"docker {mode.value} -it --name {self.docker_image} {self.docker_image} {exec_cmd}"
        elif mode == InteractMode.ATTACHING:
            command = f"docker {mode.value} -it {self.docker_image} {exec_cmd}"
        else:
            command = f"docker {mode.value} -i {self.docker_image}"

        print(f'[interactive_session] Command: {command}')

        try:
            print(f'{text_color_white}[interactive_session]{text_color_reset} '
                  f'Container: \'{text_color_blue}{self.docker_image}{text_color_reset}\' '
                  f'starting w/interactive mode: {text_color_yellow}{mode.value}{text_color_reset}.')
            completed_process = subprocess.run(command, shell=True, check=True)

            if completed_process.returncode == 0:
                print(f'{text_color_white}[interactive_session]{text_color_reset} '
                      f'Container: \'{text_color_blue}{self.docker_image}{text_color_reset}\' exited.')
            else:
                print(f'{text_color_white}[interactive_session]{text_color_reset} '
                      f'Container: \'{text_color_blue}{self.docker_image}{text_color_reset}\' '
                      f'Command exited with status code {completed_process.returncode}.')
        except subprocess.CalledProcessError as e:
            print(f'{text_color_white}[interactive_session]{text_color_reset} '
                  f'Container: \'{text_color_blue}{self.docker_image}{text_color_reset}\' Error: {e}')

    def start(self, interactive: bool = False, retry_count: int = 10):
        if self._image_exist() is not None:
            if self.restart_policy == RestartPolicy.ON_FAILURE.value:
                restart_policy_dict = {"Name": self.restart_policy, "MaximumRetryCount": retry_count}
            else:
                restart_policy_dict = {"Name": self.restart_policy}

            existing_container = self._container_exist()

            if existing_container is not None:
                restart_policy = existing_container.attrs['HostConfig']['RestartPolicy']
                if existing_container.status == 'running':
                    container_id = existing_container.short_id

                    print(f'{text_color_white}[docker_start]{text_color_reset} '
                          f'Container \'{text_color_blue}{self.docker_image}{text_color_reset}\' '
                          f'is {text_color_pink}already running{text_color_reset} (CONTAINER ID: {text_color_yellow}{container_id}{text_color_reset}, '
                          f'Restart Policy: {text_color_yellow}{restart_policy["Name"]}{text_color_reset}).')
                else:
                    if interactive:
                        self._interactive_session(InteractMode.START)
                    else:
                        existing_container.start()
                        container_id = existing_container.short_id

                        print(f'{text_color_white}[docker_start]{text_color_reset} '
                              f'Container \'{text_color_blue}{self.docker_image}{text_color_reset}\' '
                              f'is running now. (CONTAINER ID: {text_color_yellow}{container_id}{text_color_reset}).')
            else:
                print(f'{text_color_white}[docker_start]{text_color_reset} Container '
                      f'\'{text_color_blue}{self.docker_image}{text_color_reset}\' not found, creating a new one...')

                if interactive:
                    self._interactive_session(InteractMode.SPAWNING)
                else:
                    master_password = self._read_master_password()
                    container = self.client.containers.run(  # type: ignore[call-overload]
                        image=self.docker_image,
                        name=self.docker_image,
                        detach=True,
                        restart_policy=restart_policy_dict,
                        environment={"KEYMANAGER_PASSWORD": master_password}
                    )
                    container_id = container.short_id

                    print(f'{text_color_white}[docker_start]{text_color_reset} '
                          f'New container \'{text_color_blue}{self.docker_image}{text_color_reset}\' '
                          f'is running now. (CONTAINER ID: {text_color_yellow}{container_id}{text_color_reset}).')
        else:
            print(f'{text_color_white}[docker_start]{text_color_reset} Image: '
                  f'\'{text_color_blue}{self.docker_image}{text_color_reset}\' is {text_color_red}not exist.{text_color_reset}')

    def attach(self, cmd: str = ''):
        current_container = self._container_exist()
        current_status = ''

        if current_container is not None and current_container.status == 'running':
            self._interactive_session(InteractMode.ATTACHING, cmd)
        elif cmd:
            print(f'{text_color_white}[attaching]{text_color_reset} Container: '
                  f'\'{text_color_blue}{self.docker_image}{text_color_reset}\' is {text_color_red}not ready{text_color_reset}. Starting up...')
            if current_container is not None:
                current_status = current_container.status

            self.start(interactive=False)
            self._interactive_session(InteractMode.ATTACHING, cmd)

            if current_status != 'running':
                print(f'{text_color_white}[attaching]{text_color_reset} Stopping container: '
                      f'\'{text_color_blue}{self.docker_image}{text_color_reset}\' after CMD.')
                self.stop()
        else:
            # No cmd = interactive shell: auto-start if needed, keep running after
            print(f'{text_color_white}[attaching]{text_color_reset} Container: '
                  f'\'{text_color_blue}{self.docker_image}{text_color_reset}\' is {text_color_red}not ready{text_color_reset}. Starting up...')
            self.start(interactive=False)
            self._interactive_session(InteractMode.ATTACHING, cmd)
            # Container intentionally left running — it's a service

    def status(self):
        current_image = self._image_exist()
        current_container = self._container_exist()
        session_status = None

        if current_image is not None:
            status_image_name = current_image.attrs["RepoTags"][0]
            status_image_id = current_image.short_id

            if current_container is not None:
                status_container_name = current_container.name
                status_container_id = current_container.short_id
                if current_container.status == 'running':
                    session_status = f'{text_color_green}{current_container.status}{text_color_reset}'
                else:
                    session_status = f'{text_color_yellow}{current_container.status}{text_color_reset}'
            else:
                status_container_name = "N/A"
                status_container_id = "N/A"
        else:
            status_image_name = "N/A"
            status_image_id = "N/A"
            status_container_name = "N/A"
            status_container_id = "N/A"

        print(f'{text_color_white}[docker_status]{text_color_reset} '
              f'Image: {text_color_blue}{status_image_name}{text_color_reset} (IMAGE ID: {text_color_yellow}{status_image_id}{text_color_reset}), '
              f'Container: {text_color_blue}{status_container_name}{text_color_reset} (CONTAINER ID: {text_color_yellow}{status_container_id}{text_color_reset}), '
              f'Status: {session_status}')


if __name__ == '__main__':
    ctrl = DockerCtrl('DockerCtrl.config')

    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--remove', action='store_true')
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--attach', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--cmd', type=str, required=False, default='')
    parser.add_argument('--setup', action='store_true')

    args = parser.parse_args()

    if args.setup:
        ctrl.attach(cmd=ctrl.setup)

    if args.cmd:
        ctrl.attach(cmd=args.cmd)

    if args.build:
        ctrl.build()

    if args.remove:
        ctrl.remove()

    if args.start:
        ctrl.start(interactive=args.interactive)

    if args.attach:
        ctrl.attach()  # no cmd = just attach shell session

    if args.stop:
        ctrl.stop()

    if args.status:
        ctrl.status()