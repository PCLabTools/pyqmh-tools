"""
file: simulated.py
description: Simulated implementation of {{MODULE_NAME}} for development and testing.
author: Your Name (your.email@example.com)
"""

from time import sleep
from pyqmh import Message

from .factory import {{MODULE_NAME}}
from .base import Base{{MODULE_NAME}}


class Simulated{{MODULE_NAME}}(Base{{MODULE_NAME}}):
    """Simulated implementation of {{MODULE_NAME}}."""

    def background_task(self):
        """Simulated background task."""
        while self.background_task_running:
            self.logger.debug("Performing background task.")
            # TODO: implement simulated background task logic
            sleep(1)

    def greet(self, message: Message) -> bool:
        """Handles the "greet" message.

        Args:
            message (Message): Incoming message.

        Returns:
            bool: False to continue running.
        """
        self.logger.debug(f"Handling greet message: {message}")
        self.protocol.send_response(message, {"response": "Hello, World!"})
        return False


# Register this implementation with the factory.
{{MODULE_NAME}}.register("simulated", Simulated{{MODULE_NAME}})