from pathlib import Path

import pytest

from pyqmh_tools import pyqmh_project_init as project_init


def test_initialize_project_structure_creates_modules_init(tmp_path):
    src_dir, modules_dir = project_init.initialize_project_structure(tmp_path)

    assert src_dir == tmp_path / "src"
    assert modules_dir == tmp_path / "src" / "modules"
    assert (modules_dir / "__init__.py").exists()
    assert '"""Public exports of the module packages."""' in (modules_dir / "__init__.py").read_text(encoding="utf-8")


def test_create_gitignore_if_missing_creates_file(tmp_path):
    created = project_init.create_gitignore_if_missing(tmp_path)

    assert created == tmp_path / ".gitignore"
    assert created.exists()


def test_main_skips_description_prompt_if_app_exists(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "app.py").write_text("# existing app\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    def fail_input(_prompt: str):
        raise AssertionError("input should not be called when src/app.py already exists")

    monkeypatch.setattr("builtins.input", fail_input)

    project_init.main([])

    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "src" / "modules" / "__init__.py").exists()
    assert (tmp_path / "src" / "app.py").read_text(encoding="utf-8") == "# existing app\n"


def test_create_app_file_with_options_flask_copies_www_assets(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    created = project_init.create_app_file_with_options(src_dir, "project with web", use_flask_gui=True)

    assert created == src_dir / "app.py"
    app_text = created.read_text(encoding="utf-8")
    assert "from www import WebGui" in app_text
    assert "from flask import Flask" not in app_text
    assert (src_dir / "www.py").exists()
    www_py_text = (src_dir / "www.py").read_text(encoding="utf-8")
    assert "from flask import Flask" in www_py_text
    assert (src_dir / "www" / "templates" / "index.html").exists()
    assert (src_dir / "www" / "static" / "css" / "main.css").exists()


def test_main_prompts_flask_before_description_and_creates_flask_assets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    answers = iter(["yes", "project description"])

    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    project_init.main([])

    app_text = (tmp_path / "src" / "app.py").read_text(encoding="utf-8")
    assert "from www import WebGui" in app_text
    assert (tmp_path / "src" / "www.py").exists()
    assert (tmp_path / "src" / "www" / "templates" / "index.html").exists()


def test_main_help_prints_usage_and_exits(capsys):
    with pytest.raises(SystemExit) as exc_info:
        project_init.main(["--help"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "usage:" in captured.out
    assert "pyqmh_project_init" in captured.out
    assert "Initialize pyqmh project scaffolding" in captured.out
