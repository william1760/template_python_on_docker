import subprocess
import pytest
import docker
from unittest.mock import MagicMock, patch

from DockerCtrl import DockerCtrl, RestartPolicy, BashStyle, InteractMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config_file(tmp_path):
    config = tmp_path / "DockerCtrl.config"
    config.write_text(
        'docker_image="myapp"\n'
        'image_tag="latest"\n'
        'github_url="https://github.com/test/repo"\n'
        'bash_type="SH"\n'
        'restart_policy="UNLESS_STOPPED"\n'
        'setup="python main.py --setup"\n'
    )
    return str(config)


@pytest.fixture
def ctrl(config_file):
    with patch('docker.from_env'):
        return DockerCtrl(config_file)


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_parses_all_fields(self, config_file):
        with patch('docker.from_env'):
            ctrl = DockerCtrl(config_file)
        assert ctrl.docker_image == 'myapp'
        assert ctrl.image_tag == 'latest'
        assert ctrl.github_url == 'https://github.com/test/repo'
        assert ctrl.bash_type == BashStyle.SH.value
        assert ctrl.restart_policy == RestartPolicy.UNLESS_STOPPED.value
        assert ctrl.setup == 'python main.py --setup'

    def test_missing_file_exits(self, tmp_path):
        with patch('docker.from_env'):
            with pytest.raises(SystemExit):
                DockerCtrl(str(tmp_path / 'nonexistent.config'))

    def test_unknown_bash_type_defaults_empty(self, tmp_path):
        config = tmp_path / "DockerCtrl.config"
        config.write_text('docker_image="myapp"\nimage_tag="latest"\nbash_type="UNKNOWN"\n')
        with patch('docker.from_env'):
            ctrl = DockerCtrl(str(config))
        assert ctrl.bash_type == ''

    def test_unknown_restart_policy_defaults_empty(self, tmp_path):
        config = tmp_path / "DockerCtrl.config"
        config.write_text('docker_image="myapp"\nimage_tag="latest"\nrestart_policy="UNKNOWN"\n')
        with patch('docker.from_env'):
            ctrl = DockerCtrl(str(config))
        assert ctrl.restart_policy == ''

    def test_ignores_comment_lines(self, tmp_path):
        config = tmp_path / "DockerCtrl.config"
        config.write_text('% this is a comment\ndocker_image="myapp"\nimage_tag="latest"\n')
        with patch('docker.from_env'):
            ctrl = DockerCtrl(str(config))
        assert ctrl.docker_image == 'myapp'

    def test_ignores_blank_lines(self, tmp_path):
        config = tmp_path / "DockerCtrl.config"
        config.write_text('\ndocker_image="myapp"\n\nimage_tag="latest"\n')
        with patch('docker.from_env'):
            ctrl = DockerCtrl(str(config))
        assert ctrl.docker_image == 'myapp'


# ---------------------------------------------------------------------------
# _image_exist
# ---------------------------------------------------------------------------

class TestImageExist:
    def test_returns_image_when_found(self, ctrl):
        mock_image = MagicMock()
        ctrl.client.images.get.return_value = mock_image
        assert ctrl._image_exist() == mock_image

    def test_returns_none_when_not_found(self, ctrl):
        ctrl.client.images.get.side_effect = docker.errors.ImageNotFound('not found')
        assert ctrl._image_exist() is None


# ---------------------------------------------------------------------------
# _container_exist
# ---------------------------------------------------------------------------

class TestContainerExist:
    def test_returns_container_when_found(self, ctrl):
        mock_container = MagicMock()
        ctrl.client.containers.get.return_value = mock_container
        assert ctrl._container_exist() == mock_container

    def test_returns_none_when_not_found(self, ctrl):
        ctrl.client.containers.get.side_effect = docker.errors.NotFound('not found')
        assert ctrl._container_exist() is None


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------

class TestStop:
    def test_no_image_returns_false(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=None)
        assert ctrl.stop() is False

    def test_no_container_returns_false(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        assert ctrl.stop() is False

    def test_container_already_stopped_returns_true(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        mock_container.status = 'exited'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        result = ctrl.stop()
        mock_container.stop.assert_not_called()
        assert result is True

    def test_running_container_is_stopped(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        mock_container.status = 'running'
        mock_container.reload.side_effect = lambda: setattr(mock_container, 'status', 'exited')
        ctrl._container_exist = MagicMock(return_value=mock_container)
        result = ctrl.stop()
        mock_container.stop.assert_called_once()
        assert result is True

    def test_container_still_running_after_stop_returns_false(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        mock_container.status = 'running'  # stays 'running' after reload
        ctrl._container_exist = MagicMock(return_value=mock_container)
        assert ctrl.stop() is False


# ---------------------------------------------------------------------------
# remove()
# ---------------------------------------------------------------------------

class TestRemove:
    def test_no_image_does_nothing(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=None)
        ctrl.stop = MagicMock()
        ctrl.remove()
        ctrl.stop.assert_not_called()
        ctrl.client.images.remove.assert_not_called()

    def test_removes_container_and_image(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl.stop = MagicMock()
        ctrl.remove()
        mock_container.remove.assert_called_once_with(force=True)
        ctrl.client.images.remove.assert_called_once_with(ctrl.docker_image, force=True)

    def test_removes_image_when_no_container(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.stop = MagicMock()
        ctrl.remove()
        ctrl.client.images.remove.assert_called_once_with(ctrl.docker_image, force=True)

    def test_api_error_is_handled_gracefully(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.stop = MagicMock()
        ctrl.client.images.remove.side_effect = docker.errors.APIError('error')
        ctrl.remove()  # should not raise


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------

class TestBuild:
    def test_build_success(self, ctrl):
        ctrl.remove = MagicMock()
        mock_image = MagicMock()
        mock_image.short_id = 'abc123'
        ctrl.client.images.get.return_value = mock_image
        with patch('subprocess.run') as mock_run:
            ctrl.build()
            mock_run.assert_called_once()
        ctrl.remove.assert_called_once()

    def test_build_calls_remove_first(self, ctrl):
        ctrl.remove = MagicMock()
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'docker')):
            ctrl.build()
        ctrl.remove.assert_called_once()

    def test_subprocess_error_handled_gracefully(self, ctrl):
        ctrl.remove = MagicMock()
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'docker')):
            ctrl.build()  # should not raise

    def test_generic_error_handled_gracefully(self, ctrl):
        ctrl.remove = MagicMock()
        with patch('subprocess.run', side_effect=Exception('unexpected')):
            ctrl.build()  # should not raise


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestStart:
    def test_no_image_does_nothing(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=None)
        ctrl.start()
        ctrl.client.containers.run.assert_not_called()

    def test_container_already_running_does_not_restart(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        mock_container.status = 'running'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl.start()
        mock_container.start.assert_not_called()

    def test_stopped_container_is_started(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        mock_container.status = 'exited'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl.start()
        mock_container.start.assert_called_once()

    def test_stopped_container_interactive_uses_start_mode(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        mock_container = MagicMock()
        mock_container.status = 'exited'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl._interactive_session = MagicMock()
        ctrl.start(interactive=True)
        ctrl._interactive_session.assert_called_once_with(InteractMode.START)

    def test_no_container_creates_new(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start()
        ctrl.client.containers.run.assert_called_once()

    def test_no_container_interactive_spawns_new(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl._interactive_session = MagicMock()
        ctrl.start(interactive=True)
        ctrl._interactive_session.assert_called_once_with(InteractMode.SPAWNING)

    def test_on_failure_policy_includes_retry_count(self, ctrl):
        ctrl.restart_policy = RestartPolicy.ON_FAILURE.value
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start(retry_count=5)
        _, kwargs = ctrl.client.containers.run.call_args
        assert kwargs['restart_policy']['MaximumRetryCount'] == 5

    def test_non_failure_policy_excludes_retry_count(self, ctrl):
        ctrl._image_exist = MagicMock(return_value=MagicMock())
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start()
        _, kwargs = ctrl.client.containers.run.call_args
        assert 'MaximumRetryCount' not in kwargs['restart_policy']


# ---------------------------------------------------------------------------
# attach()
# ---------------------------------------------------------------------------

class TestAttach:
    def test_running_container_attaches_shell(self, ctrl):
        mock_container = MagicMock()
        mock_container.status = 'running'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl._interactive_session = MagicMock()
        ctrl.attach()
        ctrl._interactive_session.assert_called_once_with(InteractMode.ATTACHING, '')

    def test_running_container_runs_cmd(self, ctrl):
        mock_container = MagicMock()
        mock_container.status = 'running'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl._interactive_session = MagicMock()
        ctrl.attach(cmd='python main.py --run')
        ctrl._interactive_session.assert_called_once_with(InteractMode.ATTACHING, 'python main.py --run')

    def test_not_running_with_cmd_auto_starts(self, ctrl):
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start = MagicMock()
        ctrl.stop = MagicMock()
        ctrl._interactive_session = MagicMock()
        ctrl.attach(cmd='python main.py --setup')
        ctrl.start.assert_called_once()

    def test_not_running_with_cmd_auto_stops_after(self, ctrl):
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start = MagicMock()
        ctrl.stop = MagicMock()
        ctrl._interactive_session = MagicMock()
        ctrl.attach(cmd='python main.py --setup')
        ctrl.stop.assert_called_once()

    def test_was_stopped_with_cmd_also_auto_stops(self, ctrl):
        mock_container = MagicMock()
        mock_container.status = 'exited'
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl.start = MagicMock()
        ctrl.stop = MagicMock()
        ctrl._interactive_session = MagicMock()
        ctrl.attach(cmd='python main.py --setup')
        ctrl.stop.assert_called_once()

    def test_not_running_no_cmd_auto_starts(self, ctrl):
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start = MagicMock()
        ctrl.stop = MagicMock()
        ctrl._interactive_session = MagicMock()
        ctrl.attach()
        ctrl.start.assert_called_once()

    def test_not_running_no_cmd_keeps_container_running(self, ctrl):
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.start = MagicMock()
        ctrl.stop = MagicMock()
        ctrl._interactive_session = MagicMock()
        ctrl.attach()
        ctrl.stop.assert_not_called()  # service stays running


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------

class TestStatus:
    def test_no_image_prints_na(self, ctrl, capsys):
        ctrl._image_exist = MagicMock(return_value=None)
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.status()
        assert 'N/A' in capsys.readouterr().out

    def test_image_no_container(self, ctrl, capsys):
        mock_image = MagicMock()
        mock_image.attrs = {'RepoTags': ['myapp:latest']}
        mock_image.short_id = 'abc123'
        ctrl._image_exist = MagicMock(return_value=mock_image)
        ctrl._container_exist = MagicMock(return_value=None)
        ctrl.status()
        out = capsys.readouterr().out
        assert 'myapp:latest' in out
        assert 'N/A' in out

    def test_running_container(self, ctrl, capsys):
        mock_image = MagicMock()
        mock_image.attrs = {'RepoTags': ['myapp:latest']}
        mock_image.short_id = 'abc123'
        mock_container = MagicMock()
        mock_container.name = 'myapp'
        mock_container.short_id = 'def456'
        mock_container.status = 'running'
        ctrl._image_exist = MagicMock(return_value=mock_image)
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl.status()
        assert 'running' in capsys.readouterr().out

    def test_stopped_container(self, ctrl, capsys):
        mock_image = MagicMock()
        mock_image.attrs = {'RepoTags': ['myapp:latest']}
        mock_image.short_id = 'abc123'
        mock_container = MagicMock()
        mock_container.name = 'myapp'
        mock_container.short_id = 'def456'
        mock_container.status = 'exited'
        ctrl._image_exist = MagicMock(return_value=mock_image)
        ctrl._container_exist = MagicMock(return_value=mock_container)
        ctrl.status()
        assert 'exited' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _interactive_session()
# ---------------------------------------------------------------------------

class TestInteractiveSession:
    def test_spawning_uses_bash_type(self, ctrl):
        with patch('subprocess.run') as mock_run:
            ctrl._interactive_session(InteractMode.SPAWNING)
            cmd = mock_run.call_args[0][0]
            assert 'run' in cmd
            assert ctrl.bash_type in cmd

    def test_spawning_with_cmd_overrides_bash_type(self, ctrl):
        with patch('subprocess.run') as mock_run:
            ctrl._interactive_session(InteractMode.SPAWNING, cmd='python main.py --setup')
            cmd = mock_run.call_args[0][0]
            assert 'python main.py --setup' in cmd

    def test_attaching_uses_bash_type(self, ctrl):
        with patch('subprocess.run') as mock_run:
            ctrl._interactive_session(InteractMode.ATTACHING)
            cmd = mock_run.call_args[0][0]
            assert 'exec' in cmd
            assert ctrl.bash_type in cmd

    def test_attaching_with_cmd_overrides_bash_type(self, ctrl):
        with patch('subprocess.run') as mock_run:
            ctrl._interactive_session(InteractMode.ATTACHING, cmd='python main.py --run')
            cmd = mock_run.call_args[0][0]
            assert 'python main.py --run' in cmd

    def test_start_mode_uses_start_command(self, ctrl):
        with patch('subprocess.run') as mock_run:
            ctrl._interactive_session(InteractMode.START)
            cmd = mock_run.call_args[0][0]
            assert 'start' in cmd