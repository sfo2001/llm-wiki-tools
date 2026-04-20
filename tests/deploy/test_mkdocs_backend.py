from pathlib import Path
from unittest.mock import patch
from llm_wiki.deploy.mkdocs_backend import MkdocsBackend


def test_mkdocs_target_name(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    assert b.target_name == "mkdocs"


def test_mkdocs_write_page_creates_file(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    assert (tmp_path / "wiki" / "concepts" / "foo.md").exists()
    assert "# Foo" in (tmp_path / "wiki" / "concepts" / "foo.md").read_text()


def test_mkdocs_write_page_creates_parents(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.write_page("a/b/c/page.md", "# Page")
    assert (tmp_path / "wiki" / "a" / "b" / "c" / "page.md").exists()


def test_mkdocs_delete_page_removes_file(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    b.delete_page("page.md")
    assert not (tmp_path / "wiki" / "page.md").exists()


def test_mkdocs_delete_page_noop_if_missing(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.delete_page("nonexistent.md")  # must not raise


def test_mkdocs_ensure_creates_yml_if_absent(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki", name="My Research")
    b._ensure_mkdocs_yml()
    yml_path = tmp_path / "mkdocs.yml"
    assert yml_path.exists()
    content = yml_path.read_text()
    assert "My Research" in content
    assert "material" in content
    assert "docs_dir: wiki" in content


def test_mkdocs_ensure_skips_if_yml_exists(tmp_path):
    existing = tmp_path / "mkdocs.yml"
    existing.write_text("site_name: Custom\n")
    b = MkdocsBackend(tmp_path / "wiki")
    b._ensure_mkdocs_yml()
    assert "Custom" in existing.read_text()  # must not overwrite


def test_mkdocs_deploy_serve_calls_mkdocs_serve(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki", port=9000, build=False)
    with patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        b.deploy(tmp_path / "wiki")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "mkdocs" in cmd and "serve" in cmd
    assert "9000" in " ".join(str(a) for a in cmd)
    assert (tmp_path / "mkdocs.yml").exists()  # ← add this line


def test_mkdocs_deploy_build_calls_mkdocs_build(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki", build=True)
    with patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        b.deploy(tmp_path / "wiki")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "mkdocs" in cmd and "build" in cmd
