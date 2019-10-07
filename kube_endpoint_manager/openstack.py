# -*- coding: utf-8 -*-

# Copyright (c) 2019 Martin Dojcak
# See LICENSE for details.

'''External kubernetes endpoint manager module openstack
'''

import re
from typing import Optional, List

from openstack.connection import Connection as OpenStackConnection
from openstack.compute.v2._proxy import Proxy as OpenStackComputeProxy
from openstack.compute.v2.server import Server as OpenStackServer

from .external import ABCEndpoint, ABCEndpoints
from .common import MetaSingleton


class _APIClient(metaclass=MetaSingleton):
    """Openstack API client wrapper

    Instance of this class is singleton of openstack API client

    Args:
        auth_url (str): openstack auth url (keystone)
        username (str): openstack username
        password (str):  openstack password
        project_name (str):  openstack project name
        user_domain_id (Optional[str]): openstack user domain id
        project_domain_id (Optional[str]): openstack project domain id

    Properties:
        client (:obj:OpenStackConnection): openstack api client
        compute (:obj:OpenStackComputeProxy): openstack compute api client
    """
    def __init__(self,
                 auth_url: str,
                 username: str,
                 password: str,
                 project_name: str,
                 user_domain_id: Optional[str] = 'default',
                 project_domain_id: Optional[str] = 'default'):
        """Constructor
        """
        self._client = OpenStackConnection(
            auth=dict(
                auth_url=auth_url,
                username=username,
                password=password,
                project_name=project_name,
                user_domain_id=user_domain_id,
                project_domain_id=project_domain_id
            )
        )

    @property
    def client(self) -> OpenStackConnection:
        """(:obj:OpenStackConnection) openstack api client
        """
        return self._client

    @property
    def compute(self) -> OpenStackComputeProxy:
        """(:obj:OpenStackComputeProxy) openstack compute api client
        """
        return self._client.compute # pylint: disable=no-member


class Endpoint(ABCEndpoint):
    """Openstack server

    Instance of this class represents openstack endpoint for kubernetes adoption

    Args:
        server (:obj:OpenStackServer): openstack server

    Properties:
        hostname (Optional[str]): instance name
        nodename (Optional[str]): instance compute node
        address (str): instance ip addresses
        metadata (dict): instance metadata

    """
    def __init__(self, server: OpenStackServer):
        """Constructor
        """
        self._server = server
        self._network_name = self._metadata_network_name
        self._network_version = self._metadata_network_version or "4"
        self._address = self._network_address

    def __repr__(self):
        return str(
            dict(
                hostname=self.hostname,
                nodename=self.nodename,
                address=self.address,
                metadata=self.metadata,
                has_address=self.has_address
            )
        )

    @property
    def _metadata_network_name(self) -> Optional[str]:
        """(Optional[str]): openstack instance network name
        """
        network_name_key = re.compile(r'.*endpoint.network.name$')
        for key, value in self.metadata.items():
            if network_name_key.match(key):
                return str(value)
        return None

    @property
    def _metadata_network_version(self) -> Optional[str]:
        """(Optional[str]): openstack instance network version
        """
        network_version_key = re.compile(r'.*endpoint.network.version$')
        for key, value in self.metadata.items():
            if network_version_key.match(key):
                return str(value)
        return None

    def _is_network_version(self, address: dict) -> bool:
        """Check address network version

        Args:
            address (dict): OpenStackServer.addresses.address
                            (example: OpenStackServer.addresses[NETNAME][0])
        Returns:
            (bool): address version is equal as object address version
        """
        if not self._network_version:
            return True

        return bool(self._network_version == str(address['version']))

    @property
    def _has_named_network(self) -> bool:
        """(bool): check server for network named network
        """
        if not self._metadata_network_name:
            return False

        return bool(self._metadata_network_name in self._server.addresses)

    @property
    def _network_address(self) -> Optional[str]:
        """(Optional[str]): openstack instance ip
        """
        if self._has_named_network:
            # find named ip address with address version match
            for address in self._server.addresses[self._metadata_network_name]:
                if self._is_network_version(address):
                    return str(address['addr'])
        else:
            # find ip address with address version match
            for addresses in self._server.addresses.values():
                for address in addresses:
                    if self._is_network_version(address):
                        return str(address['addr'])

        # no address match selection criteria
        return None

    @property
    def hostname(self) -> str:
        """(str): instance name
        """
        return self._server.name

    @property
    def nodename(self) -> str:
        """(str): instance compute host
        """
        return self._server.compute_host

    @property
    def address(self) -> Optional[str]:
        """(Optional[str]): instance ip address
        """
        return self._address

    @property
    def metadata(self) -> dict:
        """(dict): instance metadata
        """
        return self._server.metadata

    @property
    def has_address(self) -> bool:
        """(bool): check address
        """
        return bool(self.address is not None)


class Endpoints(ABCEndpoints):
    """Openstack endpoints

    Instance of this class represents openstack endpoints for kubernetes endpoints mapping

    Args:
        auth_url (str): openstack auth url (keystone)
        username (str): openstack username
        password (str):  openstack password
        project_name (str):  openstack project name
        user_domain_id (Optional[str]): openstack user domain id
        project_domain_id (Optional[str]): openstack project domain id

        filter (dict): Filter openstack servers based on multiple filters (filters are ANDed)
            name - regexp filter on openstack instance name
            metadata - regexp filter on openstack instance metadata key and value
                key (regexp): value (regexp)

    Properties:
        endpoints (List[Endpoint]): openstack endpoints for kubernetes mapping
        addresses (List[V1EndpointAddress]): addresses of endpoints in kubernetes format

    Methods:
        refresh (None): Refresh in memory openstack endpoint
    """
    def __init__(self, auth: dict, filters: dict):
        """Constructor
        """
        super().__init__(auth=auth, filters=filters)
        self._filters = filters
        self._api = _APIClient(**auth)
        self._endpoints = self._endpoint_list()

    @staticmethod
    def is_my_type(_type: str) -> bool:
        """(bool): Factory selector helper based on type name
        """
        if _type.lower() == 'openstack':
            return True
        return False

    @staticmethod
    def _filter_server_name(server, _filter: str) -> bool:
        """Filter openstack server by name with regexp

        Args:
            _filter (str): regexp on openstack server name

        Returns:
            (bool)
        """
        return bool(re.match(_filter, server.name))

    @staticmethod
    def _filter_server_metadata(server, _filter: dict) -> bool:
        """Filter openstack server by metadata with key and value as regexp

        Args:
            _filter (dict): key (regexp): value (regexp)

        Returns:
            (bool)
        """
        def __filter(filter_key, filter_value):
            for meta_key, meta_value in server.metadata.items():
                if re.match(filter_key, meta_key):
                    if not re.match(filter_value, meta_value):
                        return False
                    return True
            return False

        for filter_key, filter_value in _filter.items():
            if not __filter(filter_key, filter_value):
                return False

        return True

    def _is_endpoint_server(self, server) -> bool:
        """Check if server match all openstack server filters for endpoint

        Args:
            server (:obj:OpenStackServer): openstack server

        Returns:
            (bool)
        """
        for name, value in self._filters.items():
            if hasattr(self, f'_filter_server_{name}'):
                if not getattr(self, f'_filter_server_{name}')(server, value):
                    return False
        return True

    def _endpoint_list(self) -> List[Endpoint]:
        """(List[Endpoint]) openstack endpoints for kubernetes mapping
        """
        endpoints = []
        for server in self._api.compute.servers():
            if self._is_endpoint_server(server):
                endpoint = Endpoint(server)
                if endpoint.has_address:
                    endpoints.append(Endpoint(server))
        return endpoints

    @property
    def endpoints(self) -> List[Endpoint]:
        """(List[Endpoint]) openstack endpoints for kubernetes mapping
        """
        return self._endpoints

    def refresh(self) -> None:
        """Sync in memory endpoints with openstack state
        """
        self._endpoints = self._endpoint_list()
