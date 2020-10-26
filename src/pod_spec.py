#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)


def make_pod_command(port: int = 27017, replica_set_name: str = None) -> dict:
    command = f"mongod --bind_ip 0.0.0.0 --port {port}"
    if replica_set_name:
        command = f"{command} --replSet {replica_set_name}"
    return command.split(" ")


def make_pod_ports(port):
    return [{"name": "mongodb", "containerPort": port, "protocol": "TCP"}]


def make_readiness_probe(port):
    return {
        "tcpSocket": {"port": port},
        "timeoutSeconds": 5,
        "periodSeconds": 5,
        "initialDelaySeconds": 10,
    }


def make_liveness_probe():
    return {
        "exec": {"command": ["pgrep", "mongod"]},
        "initialDelaySeconds": 45,
        "timeoutSeconds": 5,
    }


def make_service_account():
    return {
        "roles": [
            {
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": ["pods"],
                        "verbs": ["list"],
                    }
                ]
            }
        ]
    }


def make_pod_spec(
    image_info: dict, port: int = 27017, replica_set_name: str = None
) -> dict:
    """
    Generate the pod spec

    :param: image_info:         Object provided by
                                OCIImageResource("mongodb-image").fetch()
    :param: port:               Port for the container
    :param: replica_set_name:   Name for the replica set

    :return:                    Pod spec dictionary for the charm
    """
    command = make_pod_command(port, replica_set_name=replica_set_name)
    ports = make_pod_ports(port)
    readiness_probe = make_readiness_probe(port)
    liveness_probe = make_liveness_probe()
    service_account = make_service_account()

    return {
        "version": 3,
        "serviceAccount": service_account,
        "containers": [
            {
                "name": "mongodb",
                "imageDetails": image_info,
                "imagePullPolicy": "Always",
                "command": command,
                "ports": ports,
                "kubernetes": {
                    "readinessProbe": readiness_probe,
                    "livenessProbe": liveness_probe,
                },
            }
        ],
        "kubernetesResources": {},
    }
