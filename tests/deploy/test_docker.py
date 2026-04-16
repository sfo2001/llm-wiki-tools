import pytest
from pathlib import Path
from unittest.mock import patch
from llm_wiki.deploy.docker import DockerBackend


def test_docker_target_name(tmp_path):
    b = DockerBackend(tmp_path / "wiki")
    assert b.target_name == "docker"


def test_docker_write_page(tmp_path):
    b = DockerBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    assert (tmp_path / "wiki" / "page.md").exists()
    assert "# Page" in (tmp_path / "wiki" / "page.md").read_text()


def test_docker_delete_page(tmp_path):
    b = DockerBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    b.delete_page("page.md")
    assert not (tmp_path / "wiki" / "page.md").exists()


def test_docker_volume_command_contains_docker_run(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, port=8443, mode="volume")
    cmd = b._volume_command(wiki)
    assert "docker" in cmd
    assert "run" in cmd
    assert "nginx:alpine" in cmd
    assert "8443:80" in " ".join(cmd)
    assert str(wiki.resolve()) in " ".join(cmd)


def test_docker_image_command_contains_docker_build(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, port=8443, mode="image", tag="llm-wiki:latest")
    cmd = b._image_command(wiki)
    assert "docker" in cmd
    assert "build" in cmd
    assert "llm-wiki:latest" in cmd


def test_docker_deploy_volume_calls_docker_run(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, mode="volume")
    with patch("llm_wiki.deploy.docker.subprocess.run") as mock_run:
        b.deploy(wiki)
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "docker" in cmd and "run" in cmd


def test_docker_deploy_image_calls_docker_build(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, mode="image")
    with patch("llm_wiki.deploy.docker.subprocess.run") as mock_run:
        b.deploy(wiki)
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "docker" in cmd and "build" in cmd
