from pathlib import Path

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

    project_init.main()

    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "src" / "modules" / "__init__.py").exists()
    assert (tmp_path / "src" / "app.py").read_text(encoding="utf-8") == "# existing app\n"
