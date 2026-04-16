import pytest
from llm_wiki.deploy.base import WikiBackend


def test_wikibackend_is_abstract():
    with pytest.raises(TypeError):
        WikiBackend()


def test_concrete_subclass_works():
    from pathlib import Path

    class ConcreteBackend(WikiBackend):
        @property
        def target_name(self) -> str:
            return "test"

        def write_page(self, rel_path: str, content: str) -> None:
            pass

        def delete_page(self, rel_path: str) -> None:
            pass

        def deploy(self, wiki_dir: Path) -> None:
            pass

    b = ConcreteBackend()
    assert b.target_name == "test"
