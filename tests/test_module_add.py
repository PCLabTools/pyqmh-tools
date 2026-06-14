from pathlib import Path

import pytest

from pyqmh_tools import pyqmh_module_add as module_add


def _write_app(path: Path) -> None:
    path.write_text(
        "import logging\n"
        "import argparse\n"
        "from pyqmh import Protocol, Message\n"
        "\n"
        "class App():\n"
        "    def __init__(self, debug: bool = False):\n"
        "        self.debug = debug\n"
        "        self.address = \"main\"\n"
        "        self.protocol = Protocol(self.address)\n"
        "        # Register modules here\n"
        "\n",
        encoding="utf-8",
    )


def test_create_standard_module_updates_inits_and_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    modules_dir = tmp_path / "src" / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")
    _write_app(tmp_path / "src" / "app.py")

    created = module_add.create_standard_module("test_standard", "standard description")

    assert created.exists()
    module_init = created.parent / "__init__.py"
    assert module_init.exists()
    module_init_text = module_init.read_text(encoding="utf-8")
    assert "from .module import TestStandard" in module_init_text
    assert '__all__ = ["TestStandard"]' in module_init_text

    root_init = (tmp_path / "src" / "modules" / "__init__.py").read_text(encoding="utf-8")
    assert "from .test_standard.module import TestStandard" in root_init
    assert '"TestStandard"' in root_init

    app_text = (tmp_path / "src" / "app.py").read_text(encoding="utf-8")
    assert "from modules.test_standard import TestStandard" in app_text
    assert 'TestStandard("test_standard", self.protocol, debug=self.debug)' in app_text


def test_create_factory_module_includes_simulated_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    modules_dir = tmp_path / "src" / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")
    _write_app(tmp_path / "src" / "app.py")

    created_dir = module_add.create_factory_module("test_factory", "factory description")

    assert (created_dir / "factory.py").exists()
    assert (created_dir / "base.py").exists()
    assert (created_dir / "simulated.py").exists()

    module_init_text = (created_dir / "__init__.py").read_text(encoding="utf-8")
    assert "from .factory import TestFactory" in module_init_text
    assert "from .base import BaseTestFactory" in module_init_text
    assert "from .simulated import SimulatedTestFactory" in module_init_text
    assert '"SimulatedTestFactory"' in module_init_text


def test_create_factory_implementation_updates_module_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    modules_dir = tmp_path / "src" / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "__init__.py").write_text('__all__ = []\n', encoding="utf-8")

    module_add.create_factory_module("test_factory", "factory description")
    created = module_add.create_factory_implementation("test_factory", "hardware", "hardware impl")

    assert created.exists()
    assert created.name == "hardware.py"

    module_init_text = (created.parent / "__init__.py").read_text(encoding="utf-8")
    assert "from .hardware import HardwareTestFactory" in module_init_text
    assert '"HardwareTestFactory"' in module_init_text


def test_main_help_prints_usage_and_exits(capsys):
    with pytest.raises(SystemExit) as exc_info:
        module_add.main(["--help"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "usage:" in captured.out
    assert "pyqmh_module_add" in captured.out
    assert "Add a module scaffold" in captured.out
