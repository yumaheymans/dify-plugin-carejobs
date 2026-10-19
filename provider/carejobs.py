from typing import Any

from dify_plugin import ToolProvider


class CarejobsProvider(ToolProvider):
    """The CareJobs.Now API is public and keyless, so there is nothing to validate."""

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        return None
