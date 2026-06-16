"""
file: {{MODULE_FOLDER_NAME}}/app.py
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
from module import {{MODULE_NAME}}

class App():
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.address = "main"
        self.protocol = Protocol(self.address)
        self.logger = logging.getLogger("pyqmh.module").getChild(self.address)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        # Register modules here
        {{MODULE_NAME}}("hello_world", self.protocol, debug=self.debug)

        self._flask_app = self._create_flask_app()

    def _discover_module_web_apps(self) -> list:
        """Return sorted list of nested module names that contain a www folder."""
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

    def _template_context(self, modules: list, embedded_mode: bool) -> dict:
        """Build shared template context for standalone and embedded views."""
        base_path = "" if not embedded_mode else "/module/hello_world/app"
        show_home_about = not embedded_mode
        show_nav = show_home_about or bool(modules)
        return {
            "modules": modules,
            "show_nav": show_nav,
            "show_home_about": show_home_about,
            "embedded_mode": embedded_mode,
            "module_base_path": base_path,
        }

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
            return render_template(
                "index.html",
                **self._template_context(module_names, embedded_mode=False),
            )

        @flask_app.route("/about")
        def about():
            return render_template(
                "about.html",
                **self._template_context(module_names, embedded_mode=False),
            )

        @flask_app.route("/module/<name>")
        def module_page(name):
            if name in module_names:
                return redirect(url_for("submodule_app", name=name))
            return redirect(url_for("index"))

        @flask_app.route("/module/<name>/app/")
        @flask_app.route("/module/<name>/app/index")
        def submodule_app(name):
            if name not in module_names:
                return redirect(url_for("index"))

            templates_dir = os.path.join(src_dir, "modules", name, "www", "templates")
            index_file = os.path.join(templates_dir, "index.html")
            if not os.path.isfile(index_file):
                abort(404)

            submodule_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(["html", "xml"]),
            )
            template = submodule_env.get_template("index.html")
            return template.render(
                module_name=name,
                modules=[],
                show_nav=False,
                show_home_about=False,
                embedded_mode=False,
                module_base_path=f"/module/{name}/app",
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

        @flask_app.route("/static/<path:filename>")
        def app_static(filename):
            static_dir = os.path.join(src_dir, "www", "static")
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