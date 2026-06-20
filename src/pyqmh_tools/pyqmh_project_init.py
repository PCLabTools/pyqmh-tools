"""Initialize pyqmh project scaffolding in the current directory.

This command creates the standard folder layout and starter files needed for a
pyqmh app, with support for either the default console app scaffold or an
optional Flask web variant.

Usage:
	pyqmh_project_init [--help]

What it does:
	- Ensures src/ and src/modules/ exist.
	- Creates src/modules/__init__.py when missing.
	- Creates .gitignore from template when missing.
	- Creates src/app.py from template when missing.
	- Supports creating app.py from ``new-app.py`` or ``new-app-flask.py``.
	- Copies ``www-app`` web assets when the Flask variant is selected.
"""

from __future__ import annotations

import argparse
import getpass
import shutil
from pathlib import Path


def initialize_project_structure(base_path: Path | None = None) -> tuple[Path, Path]:
	"""Create the project directories in the call location if they do not exist."""
	root = base_path or Path.cwd()
	src_dir = root / "src"
	modules_dir = src_dir / "modules"

	src_dir.mkdir(parents=True, exist_ok=True)
	modules_dir.mkdir(parents=True, exist_ok=True)

	init_file = modules_dir / "__init__.py"
	if not init_file.exists():
		init_file.write_text(
			'"""Public exports of the module packages."""\n\n'
			'__all__ = []\n',
			encoding="utf-8",
		)

	return src_dir, modules_dir


def create_app_file(src_dir: Path, description: str) -> Path:
	"""Create src/app.py from template and replace known placeholders."""
	return create_app_file_with_options(src_dir, description, use_flask_gui=False)


def create_app_file_with_options(src_dir: Path, description: str, use_flask_gui: bool) -> Path:
	"""Create src/app.py from template, replacing placeholders and optional web assets."""
	assets_dir = Path(__file__).resolve().parent / "assets"
	template_name = "new-app-flask.py" if use_flask_gui else "new-app.py"
	template_path = assets_dir / template_name
	if not template_path.exists():
		raise FileNotFoundError(f"Template not found: {template_path}")

	destination = src_dir / "app.py"
	shutil.copy2(template_path, destination)

	content = destination.read_text(encoding="utf-8")
	content = content.replace("{{DESCRIPTION}}", description.strip())
	content = content.replace("{{AUTHOR}}", getpass.getuser())
	content = content.replace("{{MODULE_NAME}}", "MyModule")
	destination.write_text(content, encoding="utf-8")

	if use_flask_gui:
		copy_web_assets(assets_dir / "www-app", src_dir / "www")

	return destination


def copy_web_assets(source_dir: Path, destination_dir: Path) -> None:
	"""Copy web GUI assets into the destination folder if the source exists."""
	if not source_dir.exists():
		raise FileNotFoundError(f"Template directory not found: {source_dir}")

	if destination_dir.exists():
		shutil.rmtree(destination_dir)
	shutil.copytree(source_dir, destination_dir)


def create_gitignore_if_missing(root: Path) -> Path | None:
	"""Create .gitignore in project root from template when missing."""
	gitignore_path = root / ".gitignore"
	if gitignore_path.exists():
		return None

	template_path = Path(__file__).resolve().parent / "assets" / "new-.gitignore"
	if not template_path.exists():
		raise FileNotFoundError(f"Template not found: {template_path}")

	shutil.copy2(template_path, gitignore_path)
	return gitignore_path


def main(argv: list[str] | None = None) -> None:
	argparse.ArgumentParser(
		prog="pyqmh_project_init",
		description=__doc__,
		formatter_class=argparse.RawDescriptionHelpFormatter,
	).parse_args(argv)

	root = Path.cwd()
	app_exists = (root / "src" / "app.py").exists()

	try:
		src_dir, modules_dir = initialize_project_structure(root)
	except FileNotFoundError as exc:
		print(f"Error: {exc}")
		return

	print(f"Ensured directory exists: {src_dir}")
	print(f"Ensured directory exists: {modules_dir}")

	try:
		gitignore_path = create_gitignore_if_missing(root)
	except FileNotFoundError as exc:
		print(f"Error: {exc}")
		return
	if gitignore_path is not None:
		print(f"Created .gitignore file: {gitignore_path}")

	if not app_exists:
		use_flask_gui = input('Integrate a "flask" powered web gui? (y/N): ').strip().lower() in {"y", "yes"}
		description = input("App/project description: ").strip()
		try:
			app_path = create_app_file_with_options(src_dir, description, use_flask_gui)
		except FileNotFoundError as exc:
			print(f"Error: {exc}")
			return
		print(f"Created app file: {app_path}")


if __name__ == "__main__":
	main()
