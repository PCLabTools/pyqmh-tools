from pathlib import Path

import pytest

from pyqmh_tools import pyqmh_module_remove as module_remove


def _write_app(path: Path) -> None:
    path.write_text(
        "import logging\n"
        "from modules.test_factory import TestFactory\n"
        "\n"
        "class App():\n"
        "    def __init__(self, debug: bool = False):\n"
        "        self.protocol = None\n"
        "        TestFactory(\"test_factory\", self.protocol, debug=self.debug)\n"
        "\n",
        encoding="utf-8",
    )


def test_remove_module_reference_helpers(tmp_path):
    modules_dir = tmp_path / "src" / "modules"
    modules_dir.mkdir(parents=True)

    (modules_dir / "__init__.py").write_text(
        "from .test_factory.factory import TestFactory\n"
        "__all__ = [\"TestFactory\", \"BaseTestFactory\"]\n",
        encoding="utf-8",
    )
    _write_app(tmp_path / "src" / "app.py")

    removed_init = module_remove.remove_module_reference_from_modules_init(tmp_path, "test_factory")
    removed_app = module_remove.remove_module_reference_from_app(tmp_path, "test_factory")

    assert removed_init is True
    assert removed_app is True

    modules_init_text = (modules_dir / "__init__.py").read_text(encoding="utf-8")
    assert "from .test_factory.factory import TestFactory" not in modules_init_text
    assert '"TestFactory"' not in modules_init_text

    app_text = (tmp_path / "src" / "app.py").read_text(encoding="utf-8")
    assert "from modules.test_factory import TestFactory" not in app_text
    assert 'TestFactory("test_factory", self.protocol, debug=self.debug)' not in app_text


def test_main_no_modules_does_not_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fail_input(_prompt: str):
        raise AssertionError("input should not be called when no modules exist")

    monkeypatch.setattr("builtins.input", fail_input)
    module_remove.main([])


def test_main_removes_regular_module_and_references(tmp_path, monkeypatch):
    root = tmp_path
    modules_dir = root / "src" / "modules"
    target = modules_dir / "test_factory"
    target.mkdir(parents=True)
    (target / "factory.py").write_text("# factory\n", encoding="utf-8")

    (modules_dir / "__init__.py").write_text(
        "from .test_factory.factory import TestFactory\n"
        "__all__ = [\"TestFactory\"]\n",
        encoding="utf-8",
    )
    _write_app(root / "src" / "app.py")

    monkeypatch.chdir(root)
    monkeypatch.setattr(module_remove, "is_submodule", lambda *_args, **_kwargs: False)

    answers = iter(["test_factory", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    module_remove.main([])

    assert not target.exists()
    assert "test_factory" not in (modules_dir / "__init__.py").read_text(encoding="utf-8")
    assert "from modules.test_factory import TestFactory" not in (root / "src" / "app.py").read_text(encoding="utf-8")


def test_main_help_prints_usage_and_exits(capsys):
    with pytest.raises(SystemExit) as exc_info:
        module_remove.main(["--help"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "usage:" in captured.out
    assert "pyqmh_module_remove" in captured.out
    assert "Remove a module scaffold" in captured.out
