import pytest
from pathlib import Path
from unittest.mock import patch
from llm_wiki.deploy.local import LocalBackend


def test_local_target_name(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    assert b.target_name == "local"


def test_local_write_page_creates_file(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    assert (tmp_path / "wiki" / "concepts" / "foo.md").exists()
    assert "# Foo" in (tmp_path / "wiki" / "concepts" / "foo.md").read_text(encoding="utf-8")


def test_local_write_page_creates_parents(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.write_page("a/b/c/page.md", "# Page")
    assert (tmp_path / "wiki" / "a" / "b" / "c" / "page.md").exists()


def test_local_delete_page_removes_file(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    b.delete_page("page.md")
    assert not (tmp_path / "wiki" / "page.md").exists()


def test_local_delete_page_noop_if_missing(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.delete_page("nonexistent.md")  # must not raise


def test_local_server_command_fallback_to_http_server(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=8080)
    with patch("llm_wiki.deploy.local.shutil.which", return_value=None):
        cmd = b._server_command()
    joined = " ".join(cmd)
    assert "http.server" in joined
    assert "8080" in joined
    assert str(tmp_path / "wiki") in joined


def test_local_server_binds_loopback_by_default(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=8080)
    with patch("llm_wiki.deploy.local.shutil.which", return_value=None):
        cmd = b._server_command()
    assert "127.0.0.1" in cmd
    assert "0.0.0.0" not in " ".join(cmd)


def test_local_server_public_bind_uses_wildcard(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=8080, bind="0.0.0.0")
    with patch("llm_wiki.deploy.local.shutil.which", return_value=None):
        cmd = b._server_command()
    assert "0.0.0.0" in cmd


def test_local_server_command_prefers_mkdocs(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=9000)
    def which_side_effect(name):
        return "/usr/bin/mkdocs" if name == "mkdocs" else None
    with patch("llm_wiki.deploy.local.shutil.which", side_effect=which_side_effect):
        cmd = b._server_command()
    assert cmd[0] == "mkdocs"
    joined = " ".join(cmd)
    assert "9000" in joined
    assert "127.0.0.1:9000" in joined


def test_local_deploy_calls_subprocess(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=8080)
    with patch("llm_wiki.deploy.local.shutil.which", return_value=None):
        with patch("llm_wiki.deploy.local.subprocess.run") as mock_run:
            b.deploy(tmp_path / "wiki")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "http.server" in cmd
