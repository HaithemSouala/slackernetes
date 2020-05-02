#!/usr/bin/env python3
from slackernetes import k, send_file, send_message, register, run
import logging
import re


@register(r"(?:get|list) images in namespace (\S+)")
def list_images(**payload):
    """
    List images used in a namespace
    """
    namespace = re.search(payload["regex"], payload["data"]["text"]).group(1)
    message = f"Here are all the images in `{namespace}` I can find:\n" + "\n".join(
        [
            container.image
            for pod in k.list_namespaced_pod(namespace).items
            for container in pod.spec.containers
        ]
    )
    send_message(message, payload)

@register(r"list-envs")
def list_dev_env(**payload):
    """
    List prod 2.0 available namespaces
    """
    label_selector = 'env=dev'
    web_client = payload["web_client"]
    username = web_client.users_info(user=payload["data"]["user"])
    message = f"Hey <@{username['user']['id']}>, voici la liste des environnements prod 2.0:"+"\n".join(
        [f"\n `{ns.metadata.name}` {get_developer(ns.metadata.labels.get('developer'))}" for ns in k.list_namespace(label_selector=label_selector).items]
    )
    send_message(message, payload)

def get_developer(obj):
    if obj:
        return f"est utilisé par <@{obj}>"
    else:
        return "est libre :owl:"

@register(r"pick (\S+)$")
def pick_dev_env(**payload):
    """
    Pick a specific environment
    """
    label_selector = 'env=dev'
    web_client = payload["web_client"]
    namespace = re.search(payload["regex"], payload["data"]["text"]).group(1)
    username = web_client.users_info(user=payload["data"]["user"])
    namespaces = k.list_namespace(label_selector=label_selector).items
    
    k8s_ns = next(
        (
            k8s_ns
            for k8s_ns in namespaces
            if namespace in k8s_ns.metadata.name
        ),
        None,
    )

    logging.debug(f"found this k8s_ns: {k8s_ns}")
    
    if k8s_ns is None:
        message = f"Hey <@{username['user']['id']}>, l'environnement `{namespace}` n'a été trouvé." 
    elif k8s_ns and k8s_ns.metadata.labels.get('developer'):
        message = f"Hey <@{username['user']['id']}>, l'environnement `{namespace}` est utilisé par <@{k8s_ns.metadata.labels['developer']}>."
    else:
        body = {
            "metadata": {
                "labels": {
                    "developer": username['user']['id']}
                }
        }
        k.patch_namespace(namespace, body)
        message = f"Hey <!here>, l'environnement `{namespace}` a été attribué à <@{username['user']['id']}>."
    send_message(message, payload)

@register(r"release (\S+)$")
def pick_dev_env(**payload):
    """
    Pick a specific environment
    """
    label_selector = 'env=dev'
    web_client = payload["web_client"]
    namespace = re.search(payload["regex"], payload["data"]["text"]).group(1)
    username = web_client.users_info(user=payload["data"]["user"])
    namespaces = k.list_namespace(label_selector=label_selector).items
    
    k8s_ns = next(
        (
            k8s_ns
            for k8s_ns in namespaces
            if namespace in k8s_ns.metadata.name
        ),
        None,
    )

    logging.debug(f"found this k8s_ns: {k8s_ns}")
    
    if k8s_ns is None:
        message = f"Hey <@{username['user']['id']}>, l'environnement `{namespace}` n'a été trouvé."
    elif k8s_ns and k8s_ns.metadata.labels.get('developer') is None:
        message = f"Hey <@{username['user']['id']}>, l'environnement `{namespace}` est déjà libre."
    elif k8s_ns and k8s_ns.metadata.labels.get('developer') not in username['user']['id']:
        message = f"Hey <@{username['user']['id']}>, l'environnement `{namespace}` est utilisé par <@{k8s_ns.metadata.labels['developer']}>."
    else:
        body = {
            "metadata": {
                "labels": {
                    "developer": None}
                }
        }
        k.patch_namespace(namespace, body)
        message = f"Hey <!here>, l'environnement `{namespace}` est désormais libre. Bravo <@{username['user']['id']}> et à la prochaine."
    send_message(message, payload)

@register(r"(?:get|list) pods? in namespace (\S+)$")
def list_pods(**payload):
    """
    List all the Pods in a namespace
    """
    namespace = re.search(payload["regex"], payload["data"]["text"]).group(1)
    message = f"Here are all the pods in `{namespace}` I can find:\n" + "\n".join(
        [pod.metadata.name for pod in k.list_namespaced_pod(namespace).items]
    )
    send_message(message, payload)


@register(r"(?:get|list) pods?$")
def list_all_pods(**payload):
    """
    List all the Pods in a cluster
    """
    pod_list = [
        pod.metadata.name for pod in k.list_pod_for_all_namespaces(watch=False).items
    ]
    message = "Here are all the pods I can find:\n" + "\n".join(pod_list)
    send_message(message, payload)


@register(r"(?:get|list) logs? for pod (\S+)$")
def pod_logs(**payload):
    """
    Get logs for a given pod
    """
    pod_name = re.search(payload["regex"], payload["data"]["text"]).group(1)
    pod = next(
        (
            pod
            for pod in k.list_pod_for_all_namespaces(watch=False).items
            if pod_name in pod.metadata.name
        ),
        None,
    )
    logging.debug(f"found this pod: {pod}")
    if not pod:
        send_message(
            f"Could not find pod named {pod_name}. Did you type it correctly?", payload
        )
    else:
        message = (f"Here are the logs from `{pod_name}`",)
        file = k.read_namespaced_pod_log(pod_name, pod.metadata.namespace)
        send_file(message, file, payload)


@register(r"(?:get|list) previous logs? for pod (\S+)$")
def previous_pod_logs(**payload):
    """
    Get logs for a previous instance of a given pod
    """
    pod_name = re.search(payload["regex"], payload["data"]["text"]).group(1)
    pod = next(
        (
            pod
            for pod in k.list_pod_for_all_namespaces(watch=False).items
            if pod_name in pod.metadata.name
        ),
        None,
    )
    logging.debug(f"found this pod: {pod}")
    if not pod:
        send_message(
            f"Could not find pod named {pod_name}. Did you type it correctly?", payload
        )
    else:
        message = (f"Here are the logs from `{pod_name}`",)
        file = k.read_namespaced_pod_log(
            pod_name, pod.metadata.namespace, previous=True
        )
        send_file(message, file, payload)


@register(r"(get|list) namespaces$")
def list_namespaces(**payload):
    """
    List all namespaces in a cluster.
    """
    ns_list = [ns.metadata.name for ns in k.list_namespace().items]
    message = "Here are all the namespaces I can find:\n" + "\n".join(ns_list)
    send_message(message, payload)


@register(r"describe pod (.+)")
def describe_pod(**payload):
    """
    Get details about a pod include env vars and other useful info
    """
    pod_name = re.search(payload["regex"], payload["data"]["text"]).group(1)
    pod = next(
        (
            pod
            for pod in k.list_pod_for_all_namespaces(watch=False).items
            if pod_name in pod.metadata.name
        ),
        None,
    )
    logging.debug(f"found this pod: {pod}")
    if not pod:
        send_message(
            f"Could not find pod named {pod_name}. Did you type it correctly?", payload
        )
    else:
        message = (f"Here is the description for pod {pod_name}",)
        file = k.read_namespaced_pod(pod_name, pod.metadata.namespace, pretty="true")
        send_file(message, file, payload)


if __name__ == "__main__":
    run()
