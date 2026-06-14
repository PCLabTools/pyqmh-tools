from __future__ import annotations

import getpass
import re
import shutil
import subprocess
from pathlib import Path


def to_camel_case(name: str) -> str:
	"""Convert a user-provided module name into a CamelCase class name."""
	parts = re.split(r"[^A-Za-z0-9]+", name.strip())
	cleaned = [part for part in parts if part]
	if not cleaned:
		raise ValueError("Module name must contain at least one alphanumeric character.")
	return "".join(part[:1].upper() + part[1:] for part in cleaned)


def to_snake_case(name: str) -> str:
	"""Convert a user-provided module name into a snake_case directory/file name."""
	normalized = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
	normalized = re.sub(r"_+", "_", normalized).strip("_")
	if not normalized:
		raise ValueError("Module name must contain at least one alphanumeric character.")
	return normalized.lower()


def get_project_root() -> Path:
	"""Use the current working directory as the call location."""
	return Path.cwd()


def get_module_dir(module_name: str) -> Path:
	"""Return the canonical module folder path for the provided module name."""
	root = get_project_root()
	src_modules_dir = root / "src" / "modules"
	return src_modules_dir / to_snake_case(module_name)


def is_factory_module(module_dir: Path) -> bool:
	"""Check whether a module directory looks like a factory module."""
	return (module_dir / "factory.py").exists() and (module_dir / "base.py").exists()


def add_import_to_app(app_path: Path, import_line: str) -> None:
	"""Insert an import line into app.py after the last existing top-level import, if not already present."""
	content = app_path.read_text(encoding="utf-8")
	if import_line in content:
		return

	lines = content.splitlines(keepends=True)
	last_import_index = None
	for index, line in enumerate(lines):
		if re.match(r"^\s*(import |from )\S+", line):
			last_import_index = index

	if last_import_index is None:
		return

	lines.insert(last_import_index + 1, import_line + "\n")
	app_path.write_text("".join(lines), encoding="utf-8")


def register_module_in_app(module_name: str) -> bool:
	"""Add module import and constructor to src/app.py if the file exists and has a known insertion point."""
	root = get_project_root()
	app_path = root / "src" / "app.py"
	if not app_path.exists():
		return False

	module_class_name = to_camel_case(module_name)
	module_folder_name = to_snake_case(module_name)
	import_line = f"from modules.{module_folder_name} import {module_class_name}"
	constructor_fragment = f'{module_class_name}("{module_folder_name}", self.protocol, debug=self.debug)'

	text = app_path.read_text(encoding="utf-8")
	for raw_line in text.splitlines():
		line = raw_line.strip()
		if line == constructor_fragment or line == f"# {constructor_fragment}":
			return False

	lines = text.splitlines(keepends=True)
	constructor_pattern = re.compile(
		r'^\s*(?!#)[A-Za-z_][A-Za-z0-9_]*\("[^"\\]*",\s*self\.protocol,\s*debug=self\.debug\)\s*$'
	)

	marker_index = None
	for index, line in enumerate(lines):
		if "# Register modules here" in line:
			marker_index = index
			break

	insert_index = None
	indent = "        "
	if marker_index is not None:
		insert_index = marker_index + 1
		indent_match = re.match(r"^\s*", lines[marker_index])
		if indent_match:
			indent = indent_match.group(0)
	else:
		last_constructor_index = None
		for index, line in enumerate(lines):
			if constructor_pattern.match(line):
				last_constructor_index = index
		if last_constructor_index is not None:
			insert_index = last_constructor_index + 1
			indent_match = re.match(r"^\s*", lines[last_constructor_index])
			if indent_match:
				indent = indent_match.group(0)

	if insert_index is None:
		return False

	new_line = f"{indent}{constructor_fragment}\n"
	lines.insert(insert_index, new_line)
	app_path.write_text("".join(lines), encoding="utf-8")
	add_import_to_app(app_path, import_line)
	return True


def create_module_init(module_dir: Path, module_class_name: str, module_imports: str, module_exports: str) -> Path:
	"""Create __init__.py in a module folder from the new-init.py template."""
	init_template = Path(__file__).resolve().parent / "assets" / "new-init.py"
	if not init_template.exists():
		raise FileNotFoundError(f"Template not found: {init_template}")

	destination = module_dir / "__init__.py"
	shutil.copy2(init_template, destination)
	apply_template_values(
		destination,
		module_class_name,
		"",
		extra_replacements={
			"{{MODULE_IMPORTS}}": module_imports,
			"{{MODULE_EXPORTS}}": module_exports,
		},
	)
	return destination


def register_in_modules_init(module_name: str, import_line: str) -> bool:
	"""Insert import before __all__ and add class name to __all__ in src/modules/__init__.py."""
	root = get_project_root()
	modules_init = root / "src" / "modules" / "__init__.py"
	if not modules_init.exists():
		return False

	content = modules_init.read_text(encoding="utf-8")
	if import_line in content:
		return False

	# Derive the exported class name from the import line (last token after "import ")
	class_name = import_line.rsplit("import ", 1)[-1].strip()

	lines = content.splitlines(keepends=True)

	# Insert import line immediately before the __all__ line
	all_index = next(
		(i for i, ln in enumerate(lines) if re.match(r"^\s*__all__\s*=", ln)),
		None,
	)
	if all_index is not None:
		# Ensure a blank line separates imports from __all__ when needed
		prefix = lines[all_index - 1] if all_index > 0 else ""
		if prefix.strip():
			lines.insert(all_index, "\n")
			all_index += 1
		lines.insert(all_index, import_line + "\n")
		all_index += 1
	else:
		# No __all__ found — append import at end
		separator = "" if content.endswith("\n") else "\n"
		lines.append(separator + import_line + "\n")

	# Update __all__ to include the new class name
	new_lines: list[str] = []
	for ln in lines:
		if re.match(r"^\s*__all__\s*=\s*\[", ln):
			# Extract current entries
			existing = re.findall(r'"([^"]+)"|\'([^\']+)\'', ln)
			names = [a or b for a, b in existing]
			if class_name not in names:
				names.append(class_name)
			entries = ", ".join(f'"{n}"' for n in names)
			indent_match = re.match(r"^(\s*)", ln)
			indent = indent_match.group(1) if indent_match else ""
			ln = f"{indent}__all__ = [{entries}]\n"
		new_lines.append(ln)

	modules_init.write_text("".join(new_lines), encoding="utf-8")
	return True


def create_standard_module(module_name: str, module_description: str) -> Path:
	"""Create a standard module from the template under src/modules/<module_name>."""
	source_template = Path(__file__).resolve().parent / "assets" / "new-module.py"

	if not source_template.exists():
		raise FileNotFoundError(f"Template not found: {source_template}")

	module_class_name = to_camel_case(module_name)
	module_dir = get_module_dir(module_name)
	module_dir.mkdir(parents=True, exist_ok=True)

	destination_file = module_dir / "module.py"
	shutil.copy2(source_template, destination_file)

	content = destination_file.read_text(encoding="utf-8")
	content = content.replace("{{MODULE_NAME}}", module_class_name)
	content = content.replace("{{DESCRIPTION}}", module_description.strip())
	content = content.replace("{{AUTHOR}}", getpass.getuser())
	destination_file.write_text(content, encoding="utf-8")

	module_imports = f"from .module import {module_class_name}"
	module_exports = f'"{module_class_name}"'
	create_module_init(module_dir, module_class_name, module_imports, module_exports)

	import_line = f"from .{to_snake_case(module_name)}.module import {module_class_name}"
	register_in_modules_init(module_name, import_line)
	register_module_in_app(module_name)

	return destination_file


def apply_template_values(
	file_path: Path,
	module_class_name: str,
	module_description: str,
	extra_replacements: dict[str, str] | None = None,
) -> None:
	"""Replace supported placeholders in a generated file."""
	content = file_path.read_text(encoding="utf-8")
	content = content.replace("{{MODULE_NAME}}", module_class_name)
	content = content.replace("{{DESCRIPTION}}", module_description.strip())
	content = content.replace("{{AUTHOR}}", getpass.getuser())
	if extra_replacements:
		for key, value in extra_replacements.items():
			content = content.replace(key, value)
	content = content.replace("Your Name (your.email@example.com)", getpass.getuser())
	file_path.write_text(content, encoding="utf-8")


def create_factory_module(module_name: str, module_description: str) -> Path:
	"""Create a factory module from templates under src/modules/<module_name>."""
	assets_dir = Path(__file__).resolve().parent / "assets"

	module_class_name = to_camel_case(module_name)
	module_dir = get_module_dir(module_name)
	module_dir.mkdir(parents=True, exist_ok=True)

	template_map = {
		"new-factory.py": "factory.py",
		"new-base.py": "base.py",
		"new-simulated.py": "simulated.py",
	}

	for template_name, output_name in template_map.items():
		template_path = assets_dir / template_name
		if not template_path.exists():
			raise FileNotFoundError(f"Template not found: {template_path}")

		destination_file = module_dir / output_name
		shutil.copy2(template_path, destination_file)
		apply_template_values(destination_file, module_class_name, module_description)

	module_imports = (
		f"from .factory import {module_class_name}\n"
		f"from .base import Base{module_class_name}\n"
		f"from .simulated import Simulated{module_class_name}"
	)
	module_exports = f'"{module_class_name}", "Base{module_class_name}", "Simulated{module_class_name}"'
	create_module_init(module_dir, module_class_name, module_imports, module_exports)

	import_line = f"from .{to_snake_case(module_name)}.factory import {module_class_name}"
	register_in_modules_init(module_name, import_line)
	register_module_in_app(module_name)

	return module_dir


def create_factory_implementation(module_name: str, implementation_name: str, module_description: str = "") -> Path:
	"""Create a factory implementation file in an existing factory module folder."""
	assets_dir = Path(__file__).resolve().parent / "assets"
	implementation_template = assets_dir / "new-implementation.py"
	if not implementation_template.exists():
		raise FileNotFoundError(f"Template not found: {implementation_template}")

	module_dir = get_module_dir(module_name)
	if not module_dir.exists():
		raise FileNotFoundError(f"Module folder does not exist: {module_dir}")
	if not is_factory_module(module_dir):
		raise ValueError("Module exists but is not a factory module.")

	implementation_file_name = f"{to_snake_case(implementation_name)}.py"
	implementation_class_name = to_camel_case(implementation_name)
	module_class_name = to_camel_case(module_name)

	destination_file = module_dir / implementation_file_name
	shutil.copy2(implementation_template, destination_file)
	apply_template_values(
		destination_file,
		module_class_name,
		module_description,
		extra_replacements={"{{IMPLEMENTATION_NAME}}": implementation_class_name},
	)

	add_implementation_to_module_init(
		module_dir,
		to_snake_case(implementation_name),
		f"{implementation_class_name}{module_class_name}",
	)

	return destination_file


def add_implementation_to_module_init(module_dir: Path, implementation_file_stem: str, implementation_class_name: str) -> None:
	"""Add import and __all__ entry for a new implementation to the module's __init__.py."""
	module_init = module_dir / "__init__.py"
	if not module_init.exists():
		return

	import_line = f"from .{implementation_file_stem} import {implementation_class_name}"
	content = module_init.read_text(encoding="utf-8")
	if import_line in content:
		return

	lines = content.splitlines(keepends=True)

	# Insert before __all__
	all_index = next(
		(i for i, ln in enumerate(lines) if re.match(r"^\s*__all__\s*=", ln)),
		None,
	)
	if all_index is not None:
		if all_index > 0 and lines[all_index - 1].strip():
			lines.insert(all_index, "\n")
			all_index += 1
		lines.insert(all_index, import_line + "\n")
		all_index += 1
	else:
		separator = "" if content.endswith("\n") else "\n"
		lines.append(separator + import_line + "\n")

	# Update __all__
	updated: list[str] = []
	for ln in lines:
		if re.match(r"^\s*__all__\s*=\s*\[", ln):
			existing = re.findall(r"""["']([^"']+)["']""", ln)
			if implementation_class_name not in existing:
				existing.append(implementation_class_name)
			entries = ", ".join(f'"{n}"' for n in existing)
			indent_match = re.match(r"^(\s*)", ln)
			indent = indent_match.group(1) if indent_match else ""
			ln = f"{indent}__all__ = [{entries}]\n"
		updated.append(ln)

	module_init.write_text("".join(updated), encoding="utf-8")


def infer_repo_name(repo_link: str) -> str:
	"""Infer a folder name from a git repository URL."""
	clean_link = repo_link.strip().rstrip("/")
	repo_name = clean_link.split("/")[-1]
	if repo_name.endswith(".git"):
		repo_name = repo_name[:-4]

	if not repo_name:
		raise ValueError("Could not infer repository name from the provided URL.")

	return to_snake_case(repo_name)


def add_repository_module(repo_link: str, module_name: str | None = None) -> Path:
	"""Add a repository as a git submodule under src/modules/<repo_name>."""
	root = get_project_root()
	src_modules_dir = root / "src" / "modules"
	src_modules_dir.mkdir(parents=True, exist_ok=True)

	repo_folder = to_snake_case(module_name) if module_name else infer_repo_name(repo_link)
	target_path = src_modules_dir / repo_folder

	command = ["git", "submodule", "add", repo_link.strip(), str(target_path)]
	try:
		subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
	except subprocess.CalledProcessError as exc:
		error_output = (exc.stderr or exc.stdout or "").strip()
		raise RuntimeError(f"Failed to add repository submodule. {error_output}") from exc

	return target_path


def prompt_template_workflow(module_name: str) -> None:
	"""Prompt for template details and run the existing standard/factory workflow."""
	module_description = input("Module description: ").strip()
	template_type = input('Template type ("standard" or "factory"): ').strip().lower()

	if template_type == "factory":
		created_dir = create_factory_module(module_name, module_description)
		print(f"Created factory module files in: {created_dir}")
		return

	if template_type != "standard":
		print('Invalid template type. Please choose "standard" or "factory".')
		return

	created_file = create_standard_module(module_name, module_description)
	print(f"Created module file: {created_file}")


def main() -> None:
	module_name = input("Module name (snake case): ").strip()
	try:
		module_dir = get_module_dir(module_name)
	except ValueError as exc:
		print(f"Error: {exc}")
		return

	if module_dir.exists():
		if not is_factory_module(module_dir):
			print(f"Module already exists and is not a factory module: {module_dir}")
			return

		create_impl = input("Module exists as factory. Create a new implementation? (y/N): ").strip().lower()
		if create_impl in {"y", "yes"}:
			implementation_name = input("Implementation name: ").strip()
			implementation_description = input("Implementation description (optional): ").strip()
			try:
				created_file = create_factory_implementation(module_name, implementation_name, implementation_description)
			except (ValueError, FileNotFoundError, RuntimeError) as exc:
				print(f"Error: {exc}")
				return

			print(f"Created implementation file: {created_file}")
			return

		print("No changes made.")
		return

	module_type = input('Module type ("standard", "factory", or "repository"): ').strip().lower()

	if module_type == "repository":
		repo_link = input("Git repository link: ").strip()
		if not repo_link:
			print("Repository link is blank. Falling back to template workflow.")
			try:
				prompt_template_workflow(module_name)
			except (ValueError, FileNotFoundError) as exc:
				print(f"Error: {exc}")
			return

		try:
			submodule_path = add_repository_module(repo_link, module_name)
		except (ValueError, RuntimeError) as exc:
			print(f"Error: {exc}")
			return

		print(f"Added repository submodule: {submodule_path}")
		return

	module_description = input("Module description: ").strip()

	if module_type == "factory":
		try:
			created_dir = create_factory_module(module_name, module_description)
		except (ValueError, FileNotFoundError, RuntimeError) as exc:
			print(f"Error: {exc}")
			return

		print(f"Created factory module files in: {created_dir}")
		return

	if module_type != "standard":
		print('Invalid module type. Please choose "standard" or "factory".')
		return

	try:
		created_file = create_standard_module(module_name, module_description)
	except (ValueError, FileNotFoundError, RuntimeError) as exc:
		print(f"Error: {exc}")
		return

	print(f"Created module file: {created_file}")


if __name__ == "__main__":
	main()
