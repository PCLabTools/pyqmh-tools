# pyqmh-tools

Scaffolding and maintenance utilities for building a Python Queued Message Handler (QMH) project.

This repository is intended to be published as a PyPI package so the tooling can be installed with `pip` and used as project commands.

## Installation

Install from PyPI (after publish):

```bash
pip install pyqmh-tools
```

## Commands

This package provides three main commands:

1. `pyqmh_project_init`
2. `pyqmh_module_add`
3. `pyqmh_module_remove`

Note: if you see `pyqmg-module-remove` elsewhere, treat that as a typo. The command name in this project is `pyqmh_module_remove`.

---

### `pyqmh_project_init`

Initializes a new QMH project in the current directory.

What it does:

- Creates `src/` and `src/modules/` if they do not already exist.
- Creates `src/modules/__init__.py` if missing.
- Copies template `app.py` into `src/app.py` if it does not already exist.
- Prompts for app/project description (only when creating `app.py`).
- Fills template placeholders such as description/author.
- Creates root `.gitignore` from template if `.gitignore` does not exist.

Run from your target project directory:

```bash
pyqmh_project_init
```

---

### `pyqmh_module_add`

Adds a new module to `src/modules`, or adds a new implementation to an existing factory module.

Behavior summary:

- Prompts for module name first.
- If module already exists and is a factory module, prompts to add a new implementation.
- If module does not exist, prompts for module type:
  - `standard`
  - `factory`
  - `repository`

`standard` creation:

- Creates `src/modules/<module_name>/module.py` from template.
- Creates module `__init__.py` from template with imports/exports.
- Updates `src/modules/__init__.py` import and `__all__` (if file exists).
- Updates `src/app.py` import and constructor registration (if file exists).

`factory` creation:

- Creates `factory.py`, `base.py`, and `simulated.py` from templates.
- Creates module `__init__.py` from template with imports/exports.
- Includes factory/base/simulated exports.
- Updates `src/modules/__init__.py` import and `__all__` (if file exists).
- Updates `src/app.py` import and constructor registration (if file exists).

`repository` creation:

- Prompts for Git repository URL.
- Adds the repository as a Git submodule under `src/modules/<module_name>`.
- If repository URL is blank, falls back to template-based creation prompts.

Add new module:

```bash
pyqmh_module_add
```

---

### `pyqmh_module_remove`

Removes an existing module from `src/modules`.

Behavior summary:

- Prints available modules before prompting.
- Accepts module name as folder name or CamelCase class name.
- Shows files to be removed and asks for confirmation.
- If module is a Git submodule:
  - deinitializes submodule
  - removes it from Git index
  - removes submodule metadata
- If module is a regular folder:
  - removes the folder directly
- Cleans up references after removal:
  - `src/modules/__init__.py` imports and `__all__`
  - `src/app.py` import and constructor registration

Remove module:

```bash
pyqmh_module_remove
```

## Typical New Project Flow

From a new directory:

1. Initialize project scaffold.
2. Add one or more modules.
3. Run app.

Example:

```bash
mkdir my-qmh-project
cd my-qmh-project

pyqmh_project_init
pyqmh_module_add
pyqmh_module_add

python src/app.py --debug
```

## Development Notes

- Commands are designed to be run from the project root where `src/` should exist.
- The tools are idempotent for common setup steps (existing files/folders are generally preserved).
- Generated files are template-driven from `src/pyqmh_tools/assets`.
