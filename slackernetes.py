#!/usr/bin/env python3
import os
import slack
import logging
import kubernetes
import re
import time
import atexit
from slack.errors import SlackApiError

try:
    kubernetes.config.load_incluster_config()
except kubernetes.config.config_exception.ConfigException as e:
    logging.debug(
        "No in cluster config found. Trying to load config from ./kube_config..."
    )
    kubernetes.config.load_kube_config(config_file="kube_config")

k = kubernetes.client.CoreV1Api()

COMMANDS = dict()

MY_ID = ""


def register(regex):
    """
    Decorator to register function as a supported command
    """

    def decorator_register(func):
        global COMMANDS
        COMMANDS[regex] = func

    return decorator_register


def unsupported_command(**payload):
    """
    Gracefully handle unknown commands
    """
    logging.debug(f"the message text not currently handled: {payload['data']['text']}")
    return {'text': f"Sorry, I don't understand: {payload['data']['text']}"}


def for_bot(message):
    """
    Check if message is for the bot
    """
    global MY_ID
    if re.search(r"^<@" + re.escape(MY_ID) + r">.+", message.get("text")):
        return True
    else:
        return False


def send_message(message, payload):
    """
    Send a message to the channel
    """
    logging.debug(f"message type: {type(message)}")
    
    if (message is None) or (isinstance(message, str)):
        message = message
    else:
        message = message.get('text')

    try:
        response = payload["web_client"].chat_postMessage(
            channel=payload['data']['channel'], 
            text=message
            )
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["error"]


def send_file(message, file, payload):
    """
    Send a message with a file to the channel
    """
    payload["web_client"].files_upload(
        channels=payload["data"]["channel"], initial_comment=message, content=file
    )


@register(r"(help|(list|get) commands?)")
def show_help(**payload):
    """
    List all available commands
    """
    cmds = [f"{regex}    {func.__doc__}" for regex, func in COMMANDS.items()]
    message = "Here are all the supported commands:\n" + "\n".join(cmds)
    send_message(message, payload)


@slack.RTMClient.run_on(event="open")
def get_my_id(**payload):
    """
    Gets the ID for this bot user. It is used to determine which nessages the bot should respond to.
    """
    global MY_ID
    if payload["data"]["ok"]:
        MY_ID = payload["data"]["self"]["id"]

    logging.debug(f"My ID is: {MY_ID}")


@slack.RTMClient.run_on(event="message")
def handle_message(**payload):
    message = payload["data"]
    if not for_bot(message):
        return
    # all other types of submessages
    if message.get("subtype"):
        logging.debug(f"currently don't handle subtype {message['subtype']}")
        return

    (regex, func) = next(
        ((cmd, COMMANDS[cmd]) for cmd in COMMANDS if re.search(cmd, message["text"])),
        (r".*", unsupported_command),
    )
    log_request(payload, func)
    payload["regex"] = regex
    message = func(**payload)
    if (message is not None) and (message.get('file')):
        send_file(message, payload)
    else:
        send_message(message, payload)



def log_request(payload, func):
    web_client = payload["web_client"]
    username = web_client.users_info(user=payload["data"]["user"])
    channel = web_client.conversations_info(channel=payload["data"]["channel"])
    message = re.search(
        r"^<@" + re.escape(MY_ID) + r"> (.*)", payload["data"]["text"]
    ).group(1)
    logging.info(
        f"slackernetes_request{{username=\"{username['user']['name']}\",function_name=\"{func.__name__}\",channel=\"{channel.data['channel']['name']}\",message=\"{message}\"}} 1 {time.time()}"
    )


@atexit.register
def log_app_stop():
    logging.info(f'slackernetes_status{{state="stop"}} 1 {time.time()}')


def run():
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

    slack_token = os.environ["SLACK_API_TOKEN"]
    rtm_client = slack.RTMClient(token=slack_token)
    logging.info(f'slackernetes_status{{state="start"}} 1 {time.time()}')
    rtm_client.start()


__all__ = ["register", "COMMANDS", "send_message", "send_file", "run"]