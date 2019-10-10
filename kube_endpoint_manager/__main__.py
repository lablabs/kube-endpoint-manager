
#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2019 Martin Dojcak
# See LICENSE for details.

'''
External kubernetes endpoint manager
'''

import time
import logging
import warnings
import argparse
from pprint import pformat

import urllib3
import configargparse

from . import kubernetes
from . import external
from . import openstack # pylint: disable=unused-import


logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
warnings.filterwarnings(
    action="ignore",
    module=r'urllib3',
    category=urllib3.exceptions.SecurityWarning
)
warnings.filterwarnings(
    action="ignore",
    module=r'openstack',
    category=DeprecationWarning
)

log = logging.getLogger('kube-endpoint-manager') # pylint: disable=invalid-name


def args() -> argparse.Namespace:
    """Parse CLI arguments and prepare config
    """
    parser = configargparse.ArgParser(prog='kube-endpoint-manager',
                                      description='External kubernetes endpoint manager')

    parser.add(
        '--endpoint-type',
        env_var='ENDPOINT_TYPE',
        required=True,
        choices=['openstack'],
        dest='endpoint_type',
        help="External endpoint type")

    parser.add(
        '--sync-period',
        env_var='SYNC_PERIOD',
        default=5,
        type=float,
        dest='sync_period',
        help="Sync loop period")

    parser.add(
        '--k8s-namespace',
        env_var='K8S_NAMESPACE',
        required=True,
        dest='kubernetes_namespace',
        help="Kubernetes endpoint namespace")

    parser.add(
        '--k8s-endpoint',
        env_var='K8S_ENDPOINT',
        required=True,
        dest='kubernetes_endpoint',
        help="Kubernetes endpoint name")

    parser.add(
        '--k8s-api-server',
        env_var='K8S_API_SERVER',
        default=None,
        dest='kubernetes_api_server',
        help="Kubernetes API server (ip:port)")

    parser.add(
        '--k8s-api-token',
        env_var='K8S_API_TOKEN',
        default=None,
        dest='kubernetes_api_token',
        help="Kubernetes API token")

    parser.add(
        '--os-auth-url',
        env_var='OS_AUTH_URL',
        dest='openstack_auth_url',
        help="Openstack authentication URL")

    parser.add(
        '--os-username',
        env_var='OS_USERNAME',
        dest='openstack_username',
        help="Openstack authentication username")

    parser.add(
        '--os-password',
        env_var='OS_PASSWORD',
        dest='openstack_password',
        help="Openstack authentication password")

    parser.add(
        '--os-project',
        env_var='OS_PROJECT',
        dest='openstack_project',
        help="Openstack project")

    _args = parser.parse_args()

    if _args.endpoint_type == "openstack":
        _args.external_auth = dict(
            auth_url=_args.openstack_auth_url,
            username=_args.openstack_username,
            password=_args.openstack_password,
            project_name=_args.openstack_project)

    return _args


def sync_loop(config, kube_endpoint, external_endpoints):
    """Kubernetes endpoint sync loop
    """

    log.info("Starting sync loop: %fs %s -> kubernetes", config.sync_period, config.endpoint_type)

    while True:
        time.sleep(config.sync_period)

        log.info("Searching for kubernetes endpoints: %s/%s",
                 config.kubernetes_namespace, config.kubernetes_endpoint)
        kube_endpoint.refresh()
        log.info("Kubernetes endpoints fetched:\n%s", pformat(kube_endpoint.addresses))

        log.info("Searching for external endpoints "
                 "with filters:\n%s", pformat(external_endpoints.filters))
        external_endpoints.refresh()
        log.info("External endpoint fetched:\n%s", pformat(external_endpoints.addresses))

        if not kube_endpoint:
            log.info("Skipping empty kubernetes endpoints")
            continue

        if not external_endpoints:
            log.info("Skipping emtpty external endpoints")
            continue

        if kube_endpoint.addresses != external_endpoints.addresses:
            log.info("Detected diffrent external endpoint state and kubernetes state:\n%s",
                     kube_endpoint.diff(external_endpoints.addresses))
            kube_endpoint.addresses = external_endpoints.addresses
            log.info("Kubernetes endpoint state successfully updated:\n%s", kube_endpoint.addresses)
        else:
            log.info("External endpoints and kubernetes endpoints are in sync")


def main():
    """CLI entrypoint
    """
    config = args()

    kube_endpoint = kubernetes.Endpoint(
        name=config.kubernetes_endpoint,
        namespace=config.kubernetes_namespace,
        api_server=config.kubernetes_api_server,
        api_token=config.kubernetes_api_token
    )

    external_endpoints = external.factory(
        _type=config.endpoint_type,
        auth=config.external_auth,
        filters={
            'metadata': {
                '.*service.name$': f'^{config.kubernetes_endpoint}$',
                '.*service.namespace$': f'^{config.kubernetes_namespace}$',
            }
        }
    )

    sync_loop(config, kube_endpoint, external_endpoints)


if __name__ == '__main__':
    main()
