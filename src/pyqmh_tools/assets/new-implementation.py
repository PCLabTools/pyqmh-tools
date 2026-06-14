"""
file: {{IMPLEMENTATION_NAME}}.py
description: {{IMPLEMENTATION_NAME}} implementation of {{MODULE_NAME}}. {{DESCRIPTION}}
author: {{AUTHOR}}
"""

from time import sleep
from pyqmh import Message

from .factory import {{MODULE_NAME}}
from .base import Base{{MODULE_NAME}}


class {{IMPLEMENTATION_NAME}}{{MODULE_NAME}}(Base{{MODULE_NAME}}):
    """Simulated implementation of {{MODULE_NAME}}."""

    def background_task(self):
        """Simulated background task."""
        while self.background_task_running:
            self.logger.debug("Performing background task.")
            # TODO: implement simulated background task logic
            sleep(1)

    def message_custom_action(self, message: Message) -> bool:
        """Handles the custom_action message.

        Args:
            message (Message): Incoming message.

        Returns:
            bool: False to continue running.
        """
        self.logger.debug(f"Handling custom action: {message}")
        # TODO: implement simulated custom action logic
        return False


# Register this implementation with the factory.
{{MODULE_NAME}}.register("{{IMPLEMENTATION_NAME}}", {{IMPLEMENTATION_NAME}}{{MODULE_NAME}})