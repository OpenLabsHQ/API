from abc import ABC, abstractmethod

from ....enums.operating_systems import OpenLabsOS
from ....enums.specs import OpenLabsSpec


class CdktfBaseHost(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    id: str  # Unique ID given by cloud provider
    name: str
    hostname: str
    os: OpenLabsOS
    spec: OpenLabsSpec
    size: int
    tags: list[str]

    @abstractmethod
    def stop(self) -> bool:
        """Abstract method to stop the deploye host.

        Returns
        -------
            bool: True if stopped successfully. False otherwise.

        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """Abstract method to start the deployed host.

        Returns
        -------
            bool: True if started successfully. False otherwise.

        """
        pass

    @abstractmethod
    def restart(self) -> bool:
        """Abstract method to restart the deployed host.

        Returns
        -------
            bool: True if restarted successfully. False otherwise.

        """
        pass
