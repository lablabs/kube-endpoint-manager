# Kubernetes endpoint manager
Kube endpoint manager maps external endpoints to the kubernetes endpoints object. It watches for selected kubernetes endpoint object and keep it in sync with external endpoints. External endpoints are simply endpoints that lives outside of kubernetes. Manager also act as autodiscovery component, the right endpoints will be chosen based on the user rules. Currently supported autodiscovery type is only openstack. Openstack autodiscovery can target and group endpoints based on multiple conditions and transform openstack VMs to the kubernetes endpoints. Relationship between kubernetes endpoint and manager is 1:1.

Originally this is subroject of [External Service operator](https://github.com/lablabs/.external-service-operator)

## Configuration

### Common
ENV |Parameter | Description | Required | Default
--- |--- | --- | --- | --- 
`ENDPOINT_TYPE` | `--endpoint-type` | External endpoint type (openstack) | yes | None
`SYNC_PERIOD` | `--sync-period` | Sync loop period | no | `5`
`K8S_NAMESPACE` | `--k8s-namespace` | Kubernetes endpoint namespace | yes | None
`K8S_ENDPOINT` | `--k8s-endpoint` | Kubernetes endpoint name | yes | None
`K8S_API_SERVER` | `--k8s-api-server` | Kubernetes API server (ip:port) | no | `kubernetes.default.svc`
`K8S_API_TOKEN` | `--k8s-api-token` | Kubernetes Bearer token | no | `pod dtoken`

### Openstack
ENV |Parameter | Description | Required
--- |--- | --- | -- |
`FILTER_NAME` | `--filter-name` | Filter external endpoint by name (regexp) | no | None
`FILTER_METADATA` | `--filter-metadata` | Filter external endpoint by metadata in key:value format (regexp) | no | None
`OS_AUTH_URL` | `--os-auth-url` | Openstack authentication  | yes
`OS_USERNAME` | `--os-username` | Openstack authentication username | no
`OS_PASSWORD` | `--os-password` | Openstack authentication password | no
`OS_PROJECT` | `--os-project` | Openstack project | no

## Installation
### Helm Operator
Follow [External Service operator](https://github.com/lablabs/external-service-operator)

### Manual
```sh
kubectl run endpoint-manager --rm --restart=Always -it --image=lablabs/kube-endpoint-manager:latest --env ...
```

## Future
- VMware autodiscovery
- Consul autodiscovery
- [Endpoint Slices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- Health checks