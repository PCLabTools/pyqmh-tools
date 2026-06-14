"""
file: base.py
description: Base implementation contract for {{MODULE_NAME}} modules.
author: {{AUTHOR}}
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod
from pyqmh import Message, Protocol, Module


class Base{{MODULE_NAME}}(Module, ABC):
    """Abstract base class for {{MODULE_NAME}} implementations."""

    def __init__(self, address: str, protocol: Protocol, debug: Optional[bool] = None):
        """Initialises the factory module.

        Args:
            address (str): Unique address for the module.
            protocol (Protocol): The protocol instance.
            debug (bool, optional): Debug flag. Defaults to None.
        """
        super().__init__(address, protocol, debug=debug)
        self.logger = logging.getLogger("pyqmh.module").getChild(self.address)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def handle_message(self, message: Message) -> bool:
        """Handle incoming messages.

        Args:
            message (Message): The message to handle.

        Returns:
            bool: True if the module should shutdown, False otherwise.
        """
        self.logger.debug(f"Handling message: {message}")
        if message.command == "greet":
            return self.greet(message)
        return super().handle_message(message)

    @abstractmethod
    def background_task(self):
        """Background task - must be implemented by each factory implementation."""
        raise NotImplementedError("background_task must be implemented by subclasses")

    @abstractmethod
    def greet(self, message: Message) -> bool:
        """Handle the greet message - must be implemented by each factory implementation.

        Args:
            message (Message): Incoming message.

        Returns:
            bool: False to continue running.
        """
        raise NotImplementedError("greet must be implemented by subclasses")