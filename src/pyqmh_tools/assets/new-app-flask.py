"""
file: app.py
description: {{DESCRIPTION}}
author: {{AUTHOR}}
"""

import os
import logging
import argparse
import threading
from flask import Flask, render_template, redirect, url_for, send_from_directory, abort, request
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pyqmh import Protocol, Message

class App():
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.address = "main"
        self.protocol = Protocol(self.address)
        self.logger = logging.getLogger("pyqmh.module").getChild(self.address)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        # Register modules here
        # Example("ExampleModule", self.protocol, debug=self.debug)

        self._flask_app = self._create_flask_app()

    def _discover_module_web_apps(self) -> list:
        """Return sorted list of module names that contain a www folder."""
        modules_dir = os.path.join(os.path.dirname(__file__), "modules")
        if not os.path.isdir(modules_dir):
            self.logger.debug("Modules directory not found. Navigation will show no modules.")
            return []

        result = []
        for name in sorted(os.listdir(modules_dir)):
            if name.startswith("_"):
                continue
            www_path = os.path.join(modules_dir, name, "www")
            if os.path.isdir(www_path):
                result.append(name)
        return result

    def _discover_nested_module_web_apps(self, module_name: str) -> list:
        """Return nested module names for a specific module if it has its own modules folder."""
        module_modules_dir = os.path.join(
            os.path.dirname(__file__), "modules", module_name, "modules"
        )
        if not os.path.isdir(module_modules_dir):
            return []

        result = []
        for name in sorted(os.listdir(module_modules_dir)):
            if name.startswith("_"):
                continue
            www_path = os.path.join(module_modules_dir, name, "www")
            if os.path.isdir(www_path):
                result.append(name)
        return result

    def _module_has_about_page(self, module_name: str) -> bool:
        """Return True if a module provides an about.html template."""
        about_file = os.path.join(
            os.path.dirname(__file__),
            "modules",
            module_name,
            "www",
            "templates",
            "about.html",
        )
        return os.path.isfile(about_file)

    def _create_flask_app(self) -> Flask:
        """Create and configure the main Flask application."""
        src_dir = os.path.dirname(__file__)
        flask_app = Flask(
            __name__,
            template_folder=os.path.join(src_dir, "www", "templates"),
            static_folder=os.path.join(src_dir, "www", "static"),
        )

        module_names = self._discover_module_web_apps()

        @flask_app.route("/")
        def index():
            return render_template("index.html", modules=module_names)

        @flask_app.route("/about")
        def about():
            modules_with_about = [
                module for module in module_names if self._module_has_about_page(module)
            ]
            return render_template(
                "about.html",
                modules=module_names,
                modules_with_about=modules_with_about,
            )

        @flask_app.route("/module/<name>")
        def module_page(name):
            if name in module_names:
                return render_template("module_page.html", module_name=name, modules=module_names)
            return redirect(url_for("index"))

        @flask_app.route("/module/<name>/app/")
        @flask_app.route("/module/<name>/app/index")
        def module_app(name):
            if name not in module_names:
                return redirect(url_for("index"))

            templates_dir = os.path.join(src_dir, "modules", name, "www", "templates")
            index_file = os.path.join(templates_dir, "index.html")
            if not os.path.isfile(index_file):
                abort(404)

            nested_modules = self._discover_nested_module_web_apps(name)
            module_base_path = f"/module/{name}/app"

            # Render using a module-local template loader so extends/base lookups
            # resolve within that module's own templates folder.
            module_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(["html", "xml"]),
            )
            template = module_env.get_template("index.html")
            return template.render(
                module_name=name,
                modules=nested_modules,
                show_nav=bool(nested_modules),
                show_home_about=False,
                embedded_mode=True,
                module_base_path=module_base_path,
                request=request,
                url_for=url_for,
            )

        @flask_app.route("/module/<name>/app/about")
        def module_about(name):
            if name not in module_names:
                return redirect(url_for("index"))

            templates_dir = os.path.join(src_dir, "modules", name, "www", "templates")
            about_file = os.path.join(templates_dir, "about.html")
            if not os.path.isfile(about_file):
                return redirect(url_for("module_page", name=name))

            nested_modules = self._discover_nested_module_web_apps(name)
            module_base_path = f"/module/{name}/app"

            module_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(["html", "xml"]),
            )
            template = module_env.get_template("about.html")
            return template.render(
                module_name=name,
                modules=nested_modules,
                show_nav=bool(nested_modules),
                show_home_about=False,
                embedded_mode=True,
                module_base_path=module_base_path,
                request=request,
                url_for=url_for,
            )

        @flask_app.route("/module/<name>/app/static/<path:filename>")
        def module_static(name, filename):
            if name not in module_names:
                abort(404)

            static_dir = os.path.join(src_dir, "modules", name, "www", "static")
            if not os.path.isdir(static_dir):
                abort(404)
            return send_from_directory(static_dir, filename)

        @flask_app.route("/module/<name>/app/module/<sub_name>")
        @flask_app.route("/module/<name>/app/module/<sub_name>/app/")
        @flask_app.route("/module/<name>/app/module/<sub_name>/app/index")
        def nested_module_app(name, sub_name):
            if name not in module_names:
                return redirect(url_for("index"))

            nested_modules = self._discover_nested_module_web_apps(name)
            if sub_name not in nested_modules:
                return redirect(url_for("module_app", name=name))

            templates_dir = os.path.join(
                src_dir, "modules", name, "modules", sub_name, "www", "templates"
            )
            index_file = os.path.join(templates_dir, "index.html")
            if not os.path.isfile(index_file):
                abort(404)

            submodule_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(["html", "xml"]),
            )
            template = submodule_env.get_template("index.html")
            return template.render(
                module_name=sub_name,
                modules=[],
                show_nav=False,
                show_home_about=False,
                embedded_mode=True,
                module_base_path=f"/module/{name}/app/module/{sub_name}/app",
                request=request,
                url_for=url_for,
            )

        @flask_app.route("/module/<name>/app/module/<sub_name>/app/static/<path:filename>")
        def nested_module_static(name, sub_name, filename):
            if name not in module_names:
                abort(404)

            nested_modules = self._discover_nested_module_web_apps(name)
            if sub_name not in nested_modules:
                abort(404)

            static_dir = os.path.join(
                src_dir, "modules", name, "modules", sub_name, "www", "static"
            )
            if not os.path.isdir(static_dir):
                abort(404)
            return send_from_directory(static_dir, filename)

        return flask_app

    def __del__(self):
        """Clean up the main module by deleting the protocol instance.
        """
        del self.protocol

    def run(self):
        """Run the main application loop and handles application shutdown.
        """
        self.logger.debug("Starting main application loop.")

        flask_thread = threading.Thread(
            target=lambda: self._flask_app.run(
                host="0.0.0.0",
                port=5000,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
            name="flask-server",
        )
        flask_thread.start()
        self.logger.info("Flask server started on http://localhost:5000")

        print(f"\033[92mMain application loop has started. Press Ctrl+C to exit.\033[0m")

        while True:
            try:
                message = self.protocol.receive_message(self.address, timeout=0.2)
                if self.handle_message(message):
                    break
            except TimeoutError:
                continue
            except KeyboardInterrupt:
                self.logger.debug("Keyboard interrupt received. Shutting down.")
                self.protocol.broadcast_message("shutdown")
                break

    def handle_message(self, message: Message) -> bool:
        """Handle incoming messages.

        Args:
            message: The message to handle.

        Returns:
            bool: True if the message was handled successfully, False otherwise.
        """
        self.logger.debug(f"Handling message: {message}")
        if message.command == "shutdown":
            self.logger.debug("Received shutdown command. Shutting down.")
            self.protocol.broadcast_message("shutdown")
            try:
                self.protocol.receive_message(self.address, timeout=5)  # Wait for acknowledgments
            except TimeoutError:
                self.logger.debug("Timeout occurred while waiting for acknowledgments.")
            return True
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the pyqmh app.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )
    app = App(debug=args.debug)
    app.run()
    # app.run()