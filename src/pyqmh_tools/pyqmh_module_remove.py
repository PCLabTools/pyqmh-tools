"""Remove a module scaffold from a pyqmh project.

This command removes a module directory from ``src/modules`` and cleans up
references in project registration files.

Usage:
	pyqmh_module_remove [--help]

What it does:
	- Lists available modules and asks which one to remove.
	- Supports folder names or CamelCase module class names.
	- Confirms deletion before removing files.
	- Removes git submodules safely when the module is a submodule.
	- Removes matching references from src/modules/__init__.py and src/app.py.
"""

import argparse
import re
import shutil
import subprocess
from pathlib import Path


def get_project_root() -> Path:
	"""Use the current working directory as the call location."""
	return Path.cwd()


def normalize_name(name: str) -> str:
	"""Normalize free-form text to a snake-like name token."""
	normalized = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
	normalized = re.sub(r"_+", "_", normalized).strip("_")
	return normalized.lower()


def camel_to_snake(name: str) -> str:
	"""Convert CamelCase or mixedCase names to snake_case."""
	spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name.strip())
	spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", spaced)
	return normalize_name(spaced)


def resolve_module_directory(module_name_input: str, root: Path) -> Path:
	"""Resolve module folder from a user input that may be folder or class name."""
	if not module_name_input.strip():
		raise ValueError("Module name cannot be blank.")

	modules_dir = root / "src" / "modules"
	if not modules_dir.exists():
		raise FileNotFoundError(f"Modules folder not found: {modules_dir}")

	raw_name = module_name_input.strip()
	direct_candidate = modules_dir / raw_name
	if direct_candidate.is_dir():
		return direct_candidate

	candidate_names = []
	for candidate in (raw_name.lower(), normalize_name(raw_name), camel_to_snake(raw_name)):
		if candidate and candidate not in candidate_names:
			candidate_names.append(candidate)

	matches = [modules_dir / candidate for candidate in candidate_names if (modules_dir / candidate).is_dir()]
	if len(matches) == 1:
		return matches[0]

	if len(matches) > 1:
		names = ", ".join(match.name for match in matches)
		raise ValueError(f"Module name is ambiguous. Matches: {names}")

	raise FileNotFoundError(f"No module folder found for '{module_name_input}'.")


def list_module_entries(module_dir: Path) -> list[str]:
	"""List all files and folders beneath the module folder for deletion confirmation."""
	entries: list[str] = []
	for path in sorted(module_dir.rglob("*")):
		relative = path.relative_to(module_dir).as_posix()
		if path.is_dir():
			entries.append(f"{relative}/")
		else:
			entries.append(relative)
	return entries


def is_submodule(module_dir: Path, root: Path) -> bool:
	"""Return True when the target folder is tracked as a git submodule."""
	rel_path = module_dir.relative_to(root).as_posix()
	result = subprocess.run(
		["git", "submodule", "status", "--", rel_path],
		cwd=root,
		capture_output=True,
		text=True,
	)
	return result.returncode == 0 and bool(result.stdout.strip())


def remove_submodule(module_dir: Path, root: Path) -> None:
	"""Remove submodule and update git index/config."""
	rel_path = module_dir.relative_to(root).as_posix()

	deinit = subprocess.run(
		["git", "submodule", "deinit", "-f", "--", rel_path],
		cwd=root,
		capture_output=True,
		text=True,
	)
	if deinit.returncode != 0:
		error_output = (deinit.stderr or deinit.stdout or "").strip()
		raise RuntimeError(f"Failed to deinitialize submodule. {error_output}")

	rm = subprocess.run(
		["git", "rm", "-f", rel_path],
		cwd=root,
		capture_output=True,
		text=True,
	)
	if rm.returncode != 0:
		error_output = (rm.stderr or rm.stdout or "").strip()
		raise RuntimeError(f"Failed to remove submodule. {error_output}")

	git_modules_path = root / ".git" / "modules" / Path(rel_path)
	if git_modules_path.exists():
		shutil.rmtree(git_modules_path)


def remove_regular_module(module_dir: Path) -> None:
	"""Remove a regular module directory."""
	shutil.rmtree(module_dir)


def snake_to_camel(name: str) -> str:
	"""Convert snake_case text to CamelCase."""
	parts = [part for part in name.split("_") if part]
	return "".join(part[:1].upper() + part[1:] for part in parts)


def remove_module_reference_from_modules_init(root: Path, module_folder_name: str) -> bool:
	"""Remove import lines and __all__ entries for the module from src/modules/__init__.py."""
	modules_init = root / "src" / "modules" / "__init__.py"
	if not modules_init.exists():
		return False

	module_class_name = snake_to_camel(module_folder_name)
	import_pattern = re.compile(
		rf'^\s*from\s+\.{re.escape(module_folder_name)}\.[^\s]+\s+import\s+.*$'
	)

	lines = modules_init.read_text(encoding="utf-8").splitlines(keepends=True)
	filtered: list[str] = []
	removed_any = False

	for line in lines:
		if import_pattern.match(line.rstrip()):
			removed_any = True
			continue
		filtered.append(line)

	# Update __all__: remove entries matching the module class name or Base<ClassName>
	names_to_remove = {module_class_name, f"Base{module_class_name}"}
	updated: list[str] = []
	for line in filtered:
		if re.match(r'^\s*__all__\s*=\s*\[', line):
			existing = re.findall(r"""["']([^"']+)["']""", line)
			names = [n for n in existing if n not in names_to_remove]
			entries = ", ".join(f'"{n}"' for n in names)
			indent_match = re.match(r'^(\s*)', line)
			indent = indent_match.group(1) if indent_match else ""
			line = f"{indent}__all__ = [{entries}]\n"
			removed_any = True
		updated.append(line)

	if removed_any:
		modules_init.write_text("".join(updated), encoding="utf-8")

	return removed_any


def remove_module_reference_from_app(root: Path, module_folder_name: str) -> bool:
	"""Remove matching import and constructor references from src/app.py when present."""
	app_path = root / "src" / "app.py"
	if not app_path.exists():
		return False

	module_class_name = snake_to_camel(module_folder_name)
	valid_addresses = {module_folder_name, module_class_name}
	import_pattern = re.compile(
		rf'^\s*from\s+modules\.{re.escape(module_folder_name)}\s+import\s+\S+\s*$'
	)
	constructor_pattern = re.compile(
		rf'^\s*#?\s*{re.escape(module_class_name)}\("(?P<address>[^"]+)",\s*self\.protocol,\s*debug=self\.debug\)\s*$'
	)

	lines = app_path.read_text(encoding="utf-8").splitlines(keepends=True)
	filtered_lines: list[str] = []
	removed_any = False

	for line in lines:
		if import_pattern.match(line.rstrip()):
			removed_any = True
			continue
		match = constructor_pattern.match(line.strip())
		if match and match.group("address") in valid_addresses:
			removed_any = True
			continue
		filtered_lines.append(line)

	if removed_any:
		app_path.write_text("".join(filtered_lines), encoding="utf-8")

	return removed_any


def main(argv: list[str] | None = None) -> None:
	argparse.ArgumentParser(
		prog="pyqmh_module_remove",
		description=__doc__,
		formatter_class=argparse.RawDescriptionHelpFormatter,
	).parse_args(argv)

	root = get_project_root()
	modules_dir = root / "src" / "modules"

	if modules_dir.exists():
		available = [p.name for p in sorted(modules_dir.iterdir()) if p.is_dir()]
		if available:
			print("Available modules:")
			for name in available:
				print(f"  - {name}")
		else:
			print("No modules found.")
			return
	else:
		print("No modules folder found.")
		return

	module_name_input = input("\nModule name (CamelCase class or folder name): ").strip()

	try:
		module_dir = resolve_module_directory(module_name_input, root)
	except (ValueError, FileNotFoundError) as exc:
		print(f"Error: {exc}")
		return

	print(f"\nModule folder: {module_dir}")
	entries = list_module_entries(module_dir)
	if entries:
		print("Contents to be deleted:")
		for entry in entries:
			print(f"- {entry}")
	else:
		print("Module folder is empty.")

	confirm = input("Confirm deletion? (y/N): ").strip().lower()
	if confirm not in {"y", "yes"}:
		print("Deletion cancelled.")
		return

	module_folder_name = module_dir.name

	try:
		if is_submodule(module_dir, root):
			remove_submodule(module_dir, root)
			print("Removed git submodule and updated git index.")
		else:
			remove_regular_module(module_dir)
			print("Removed module folder.")
	except RuntimeError as exc:
		print(f"Error: {exc}")
		return

	if remove_module_reference_from_modules_init(root, module_folder_name):
		print("Removed module reference(s) from src/modules/__init__.py.")

	if remove_module_reference_from_app(root, module_folder_name):
		print("Removed matching module reference(s) from src/app.py.")


if __name__ == "__main__":
	main()
