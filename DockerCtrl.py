import docker
import subprocess
import argparse
from docker import errors
from enum import Enum

#setting color coding
text_color_red = '\033[31m'
text_color_green = '\033[32m'
text_color_yellow = '\033[33m'
text_color_white = '\033[37m'
text_color_blue = '\033[34m'
text_color_reset = '\033[0m'
text_color_purple = '\033[35m'
text_color_pink = '\033[95m'

# Initialize variables
docker_image = None
github_url = None
image_tag = None
selected_bash_type = None
selected_restart_policy_type = None
config_file = None
manual_cmd = False
setup = ''

client = docker.from_env()

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


def init_config(file):
    global docker_image, github_url, image_tag, client, selected_bash_type, config_file, selected_restart_policy_type, setup

    bash_type = None
    restart_policy_type = None
    config_file = file

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

        key, value = map(str.strip, line.split('=', 1))

        if key == 'docker_image':
            docker_image = value.strip('"')
        elif key == 'github_url':
            github_url = value.strip('"')
        elif key == 'image_tag':
            image_tag = value.strip('"')
        elif key == 'bash_type':
            bash_type = value.strip('"')
        elif key == 'setup':
            setup = value.strip('"')
        elif key == 'restart_policy':
            restart_policy_type = value.strip('"')

    for enum_member in BashStyle:
        if enum_member.name == bash_type:
            selected_bash_type = enum_member.value
            break

    for enum_member in RestartPolicy:
        if enum_member.name == restart_policy_type:
            selected_restart_policy_type = enum_member.value
            break

    print(f'{text_color_white}[read_config]{text_color_reset} Variable: '
          f'docker_image = \'{text_color_blue}{docker_image}{text_color_reset}\' | '
          f'github_url = \'{text_color_blue}{github_url}{text_color_reset}\' | '
          f'image_tag = \'{text_color_blue}{image_tag}{text_color_reset}\' | '
          f'restart_policy = \'{text_color_blue}{restart_policy_type}{text_color_reset}\' | '
          f'bash_type = \'{text_color_blue}{selected_bash_type}{text_color_reset}\' | '
          f'setup = \'{text_color_blue}{setup}{text_color_reset}\'')


def image_exist():
    try:
        image = client.images.get(f'{docker_image}:{image_tag}')
    except docker.errors.ImageNotFound:
        return None

    return image


def container_exist():
    try:
        container = client.containers.get(docker_image)
    except docker.errors.NotFound:
        return None

    return container


def docker_stop():
    if not image_exist() is None:
        container = container_exist()

        if not container is None:
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
                  f"Error: Container \'{text_color_blue}{docker_image}{text_color_reset}\' not found")
            return False
    else:
        print(f'{text_color_white}[docker_stop]{text_color_reset} '
              f'The image \'{text_color_red}{docker_image}:{image_tag}{text_color_reset}\' does not exist.')
        return False


def docker_remove():
    if not image_exist() is None:
        try:
            docker_stop()

            print(f'{text_color_white}[docker_remove]{text_color_reset} '
                  f'Removing docker image: \'{text_color_blue}{docker_image}{text_color_reset}\'...')
            client.images.remove(docker_image, force=True)

            print(f'{text_color_white}[docker_remove]{text_color_reset} '
                  f'Removing docker container: \'{text_color_blue}{docker_image}{text_color_reset}\'...')
            client.containers.get(docker_image).remove(force=True)
        except docker.errors.APIError:
            print(f'{text_color_white}[docker_remove]{text_color_reset} '
                  f'Error occurred while remove the image & container \'{text_color_blue}{docker_image}{text_color_reset}\'.')
    else:
        print(f'{text_color_white}[docker_remove]{text_color_reset} '
              f'The image \'{text_color_red}{docker_image}:{image_tag}{text_color_reset}\' does not exist.')


def docker_build():
    docker_remove()

    try:
        print(f'{text_color_white}[docker_build]{text_color_reset} '
              f'Building Docker image \'{docker_image}\'...')

        subprocess.run(['docker', 'build', '--build-arg', f'FOLDER_NAME={docker_image}', '-t', f'{docker_image}:{image_tag}', '.'], check=True)

        image_id = client.images.get(docker_image).short_id

        if image_id:
            print(f'{text_color_white}[docker_build]{text_color_reset} '
                  f'Docker image  \'{text_color_blue}{docker_image}{text_color_reset}\' '
                  f'built successfully (IMAGE ID: {text_color_yellow}{image_id}{text_color_reset}).')
    except subprocess.CalledProcessError as e:
        print(f'{text_color_white}[docker_build]{text_color_reset} Build failed: {e}')
    except Exception as e:
        print(f'{text_color_white}[docker_build]{text_color_reset} Build failed: {e}')


def interactive_session(mode:InteractMode):
    if mode == InteractMode.SPAWNING:
        command = f"docker {mode.value} -it --name {docker_image} {docker_image} {selected_bash_type}"
    elif mode == InteractMode.ATTACHING:
        command = f"docker {mode.value} -it {docker_image} {selected_bash_type}"
    else:
        command = f"docker {mode.value} -i {docker_image}"

    print(f'[interactive_session] Command: {command}')

    try:
        print(f'{text_color_white}[interactive_session]{text_color_reset} '
              f'Container: \'{text_color_blue}{docker_image}{text_color_reset}\' '
              f'starting w/interactive mode: {text_color_yellow}{mode.value}{text_color_reset}.')
        completed_process = subprocess.run(command, shell=True, check=True)

        if completed_process.returncode == 0:
            print(f'{text_color_white}[interactive_session]{text_color_reset} '
                  f'Container: \'{text_color_blue}{docker_image}{text_color_reset}\' exited.')
        else:
            print(f'{text_color_white}[interactive_session]{text_color_reset} '
                  f'Container: \'{text_color_blue}{docker_image}{text_color_reset}\' '
                  f'Command exited with status code {completed_process.returncode}.')
    except subprocess.CalledProcessError as e:
        print(f'{text_color_white}[interactive_session]{text_color_reset} '
              f'Container: \'{text_color_blue}{docker_image}{text_color_reset}\' Error: {e}')


def docker_start(interactive:bool = False, retry_count = 10, manual_cmd:str = ''):
    if not image_exist() is None:
        if selected_restart_policy_type == RestartPolicy.ON_FAILURE.value:
            restart_policy_dict = {
                "Name": selected_restart_policy_type,
                "MaximumRetryCount": retry_count
            }
        else:
            restart_policy_dict = {
                "Name": selected_restart_policy_type
            }

        existing_container = container_exist()

        if existing_container is None:
            print(f'{text_color_white}[docker_start]{text_color_reset} Container '
                  f'\'{text_color_blue}{docker_image}{text_color_reset}\' is {text_color_red}not created{text_color_reset}.')

        if not existing_container is None:
            restart_policy = existing_container.attrs['HostConfig']['RestartPolicy']
            if existing_container.status == 'running':
                container_id = existing_container.short_id

                print(f'{text_color_white}[docker_start]{text_color_reset} '
                      f'Container \'{text_color_blue}{docker_image}{text_color_reset}\' '
                      f'is {text_color_pink}already running{text_color_reset} (CONTAINER ID: {text_color_yellow}{container_id}{text_color_reset}, '
                      f'Restart Policy: {text_color_yellow}{restart_policy["Name"]}{text_color_reset}).')
            else:
                if interactive:
                    interactive_session(InteractMode.START)
                else:
                    existing_container.start()
                    container_id = existing_container.short_id

                    print(f'{text_color_white}[docker_start]{text_color_reset} '
                          f'Container \'{text_color_blue}{docker_image}{text_color_reset}\' '
                          f'is running now. (CONTAINER ID: {text_color_yellow}{container_id}{text_color_reset}).')
        else:
            if interactive:
                interactive_session(InteractMode.SPAWNING)
            else:
                container = client.containers.run(
                    image=docker_image,
                    name=docker_image,
                    detach=True,
                    restart_policy=restart_policy_dict
                )
                container_id = container.short_id

                print(f'{text_color_white}[docker_start]{text_color_reset} '
                      f'New container \'{text_color_blue}{docker_image}{text_color_reset}\' '
                      f'is running now. (CONTAINER ID: {text_color_yellow}{container_id}{text_color_reset}).')
    else:
        print(f'{text_color_white}[docker_start]{text_color_reset} Image: '
              f'\'{text_color_blue}{docker_image}{text_color_reset}\' is {text_color_red}not exist.{text_color_reset}')


def attaching():
    current_container = container_exist()
    current_status = ''

    if not current_container is None and current_container.status == 'running':
        interactive_session(InteractMode.ATTACHING)
    elif manual_cmd:
        print(f'{text_color_white}[attaching]{text_color_reset} Container: '
              f'\'{text_color_blue}{docker_image}{text_color_reset}\' is {text_color_red}not ready{text_color_reset}. Starting up...')
        if not current_container is None:
            current_status = current_container.status

        docker_start(interactive=False)
        interactive_session(InteractMode.ATTACHING)

        if not current_status == 'running':
            print(f'{text_color_white}[attaching]{text_color_reset} Stopping container: '
                  f'\'{text_color_blue}{docker_image}{text_color_reset}\' after CMD.')
            docker_stop()
    else:
        if current_container is None:
            print(f'{text_color_white}[attaching]{text_color_reset} Container: '
                  f'\'{text_color_blue}{docker_image}{text_color_reset}\' is {text_color_red}not created.{text_color_reset}.')
        else:
            print(f'{text_color_white}[attaching]{text_color_reset} Container: '
                  f'\'{text_color_blue}{docker_image}{text_color_reset}\' is {text_color_red}not running.{text_color_reset}')


def docker_status():
    session_status = None

    current_image = image_exist()
    current_container = container_exist()

    if not current_image is None:
        status_image_name = current_image.attrs["RepoTags"][0]
        status_image_id = current_image.short_id

        if not current_container is None:
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
    init_config('DockerCtrl.config')

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
        selected_bash_type = setup

    if args.cmd:
        selected_bash_type = args.cmd

    if args.setup or args.cmd:
        manual_cmd = True
        attaching()

    if args.build:
        docker_build()

    if args.remove:
        docker_remove()

    if args.start:
        docker_start(interactive=args.interactive)

    if args.attach:
        attaching()

    if args.stop:
        docker_stop()

    if args.status:
        docker_status()
