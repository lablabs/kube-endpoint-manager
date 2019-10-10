# -*- coding: utf-8 -*-

# Copyright (c) 2019 Martin Dojcak
# See LICENSE for details.

'''External kubernetes endpoint manager interface for external endpoints
'''

from typing import Optional, List
from abc import ABC, abstractmethod

from kubernetes.client.models import V1EndpointAddress


class ABCEndpoint(ABC):
    """External endpoint abstract base class
    """
    @property
    @abstractmethod
    def hostname(self) -> str:
        """(str): instance name
        """

    @property
    @abstractmethod
    def nodename(self) -> str:
        """(str): instance compute host
        """

    @property
    @abstractmethod
    def address(self) -> Optional[str]:
        """(Optional[str]): instance ip address
        """

    @property
    @abstractmethod
    def metadata(self) -> dict:
        """(dict): instance metadata
        """

class ABCEndpoints(ABC):
    """External endpoints abstract base class
    """
    @abstractmethod
    def __init__(self, auth: dict, filters: dict, *args, **kwargs):
        """Constructor
        """
        self._filters = filters

    def __bool__(self):
        if self.addresses:
            return True

        return False

    def __repr__(self):
        return str(self.addresses)

    @staticmethod
    @abstractmethod
    def is_my_type(_type: str) -> bool:
        """(bool): Factory selector helper based on type name
        """

    @property
    def filters(self):
        """(dict): External endpoint filters
        """
        return self._filters

    @property
    @abstractmethod
    def endpoints(self) -> List[ABCEndpoint]:
        """(List[Endpoint]) openstack endpoints for kubernetes mapping
        """

    @property
    def addresses(self) -> List[V1EndpointAddress]:
        """(List[V1EndpointAddress]) addresses of endpoints in kubernetes format
        """
        addresses = []

        for endpoint in self.endpoints:
            addresses.append(
                V1EndpointAddress(
                    hostname=endpoint.hostname,
                    node_name=endpoint.nodename,
                    ip=endpoint.address
                )
            )

        return addresses

    @abstractmethod
    def refresh(self) -> None:
        """Sync in memory endpoints with openstack state
        """

def factory(_type: str, *args, **kwargs) -> Optional[ABCEndpoints]:
    """Endpoint factory based on type
    """
    for cls in ABCEndpoints.__subclasses__():  # pylint: disable=no-member
        if cls.is_my_type(_type):
            return cls(*args, **kwargs)
    return None
