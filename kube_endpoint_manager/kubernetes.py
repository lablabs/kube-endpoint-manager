# -*- coding: utf-8 -*-

# Copyright (c) 2019 Martin Dojcak
# See LICENSE for details.

'''External kubernetes endpoint manager module kubernetes
'''

from typing import Optional, List

from deepdiff import DeepDiff
from kubernetes.client.rest import ApiException
from kubernetes.client import ApiClient, CoreV1Api, Configuration
from kubernetes.client.models import V1Endpoints, V1EndpointAddress
from kubernetes.client.models.v1_endpoint_port import V1EndpointPort

from .common import MetaSingleton


class _APIClient(metaclass=MetaSingleton):
    """Kubernetes API client wrapper

    Instance of this class is singleton of kubernetes API client

    Args:
        api_server (Optional[str]): kubernetes api server in host:port format
        api_token (Optional[str]): kubernetes bearer token, default token from
                                   /var/run/secrets/kubernetes.io/serviceaccount/token

    Properties:
        api_server (str): kubernetes connection string
        api_token (str): kubernetes api bearer token
        client (:obj:ApiClient): kubernetes api client
    """
    def __init__(self,
                 api_server: Optional[str] = None,
                 api_token: Optional[str] = None):
        """Constructor
        """
        if not hasattr(self, '_configuration') or not hasattr(self, '_client'):
            self._api_server = api_server or 'kubernetes.default.svc'
            self._api_token = api_token

            self._configuration = Configuration()
            self._configuration.verify_ssl = False
            self._configuration.api_key_prefix['authorization'] = 'Bearer'
            self._configuration.host = self._connection
            self._configuration.api_key['authorization'] = self._token

            self._client = ApiClient(self._configuration)

    @property
    def _connection(self) -> str:
        """(str): kubernetes connection string
        """
        return f"https://{self._api_server}"

    @property
    def _token(self) -> str:
        """(str): kubernetes bearer token
        """
        if self._api_token:
            return self._api_token

        with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as token:
            return str(token.read())

    @property
    def api_server(self) -> str:
        """(str): kubernetes connection string
        """
        return str(self._client.configuration.host)

    @property
    def api_token(self) -> str:
        """(str): kubernetes bearer token
        """
        return str(self._client.configuration.api_key['authorization'])

    @property
    def client(self) -> ApiClient:
        """(:obj:ApiClient) kubernetes API client
        """
        return self._client


class _APICoreV1(CoreV1Api):
    """Kubernetes API core/v1 client wrapper

    Instance of this class represents kubernetes API core/v1 client
    """
    def __init__(self, *args, **kwargs):
        self._api_client = _APIClient(*args, **kwargs)
        super().__init__(self._api_client.client)


class Endpoint:
    """Kubernetes endpoints object

    Instance of this represent kubernets endpoint object

    Args:
        name (str): kubernetes endpoint name
        namespace(str): kubernetes endpoint namespace
        api_server (Optional[str]): kubernetes api server in host:port format
        api_token (Optional[str]): kubernetes bearer token, default token from
                                   /var/run/secrets/kubernetes.io/serviceaccount/token

    Properties:
        name (Optional[str]): kubernetes endpoint name
        namespace (Optional[str]): kubernetes endpoint namespace
        ports (List[V1EndpointPort]): kubernetes endpoint subset ports
        addresses (List[V1EndpointAddress]): get addresses (also setter)

    Methods:
        refresh (None): Refresh in memory kubernetes endpoint object
        diff (dict): comapre addresses

    """
    def __init__(self, name, namespace, api_server=None, api_token=None):
        self._name = name
        self._namespace = namespace
        self._api = _APICoreV1(api_server=api_server, api_token=api_token)
        self._endpoint = self._read_endpoint()

    def __bool__(self):
        """(bool): check for existence of endpoint in kubernetes
        """
        if self._endpoint:
            return True

        return False

    def __repr__(self):
        return repr(self.addresses)

    def _read_endpoint(self) -> Optional[V1Endpoints]:
        """(Optional[V1Endpoints]): return endpoint object
        """
        try:
            return self._api.read_namespaced_endpoints(name=self._name,
                                                       namespace=self._namespace)
        except ApiException:
            pass

        return None

    @property
    def name(self) -> Optional[str]:
        """(Optional[str]): endpoint name
        """
        if not self._endpoint:
            return None

        return str(self._endpoint.metadata.name)

    @property
    def namespace(self) -> Optional[str]:
        """(Optional[str]): endpoint namespace
        """
        if not self._endpoint:
            return None

        return str(self._endpoint.metadata.namespace)

    def _patch_addresses(self, addresses: List[V1EndpointAddress]) -> V1Endpoints:
        """Patch kubernetes endpoint subsets addresses

        Args:
            addresses (List[V1EndpointAddress]): new endpoint subset addresses

        Returns:
            V1Endpoints: new endpoint subset addresses
        """
        body = {
            "subsets": [
                {
                    "addresses": addresses,
                    "ports": self.ports
                }
            ]
        }

        return self._api.patch_namespaced_endpoints(
            name=self.name,
            namespace=self.namespace,
            body=body,
            field_manager=f'kube-endpoint-manager-{self.namespace}-{self.name}'
        )

    def refresh(self) -> None:
        """Sync in memory endpoint with kubernetes state
        """
        self._endpoint = self._read_endpoint()

    @property
    def addresses(self) -> List[V1EndpointAddress]:
        """Get/Set kubernetes endpoint subset addresses

        Patch kubernetes endpoint object with new list of subset addresses

        Returns:
            (List[V1EndpointAddress]): kubernetes endpoint subset addresses
        """
        if not self._endpoint or not self._endpoint.subsets[0].addresses:
            return []

        return list(self._endpoint.subsets[0].addresses)

    @addresses.setter
    def addresses(self, value) -> None:
        """
        """
        if self._endpoint and self.diff(value):
            self._patch_addresses(value)
            self.refresh()

    @property
    def ports(self) -> List[V1EndpointPort]:
        """(List[V1EndpointPort]): kubernetes endpoint subset ports
        """
        return list(self._endpoint.subsets[0].ports)

    def diff(self, addresses: List[V1EndpointAddress]) -> dict:
        """Diff addresses

        Args:
            addresses (List[V1EndpointAddress]): endpoint addresses to compare

        Returns:
            (dict): addresses diffrence in text representation or empty dict
        """
        if not self._endpoint:
            return None
        return DeepDiff(self.addresses, addresses).to_dict()
