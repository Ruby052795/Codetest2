# features/environment.py
import websocket
import json
import logging


WEBSOCKET_URL = "wss://uat-stream.3ona.co/exchange/v1/market"

def before_all(context):
    pass


def after_all(context):
    # close Websocket connection
    if hasattr(context, 'ws') and context.ws:
        context.ws.close()
        logging.info("WebSocket Connection closed")

def before_scenario(context, scenario):
    # create Websocket connection
    try:
        context.ws = websocket.create_connection(WEBSOCKET_URL, timeout=5)
        logging.info("WebSocket Connection opened")
    except Exception as e:
        logging.error(f"Failed to connect to {WEBSOCKET_URL}: {e}")
        raise

    try:
        context.ws = websocket.create_connection(
            WEBSOCKET_URL,
            timeout=10,
            ping_interval=20,
            ping_timeout=5
        )

        logging.info("WebSocket Connection opened for new scenario.")
    except Exception as e:
        logging.error(f"Failed to connect to {WEBSOCKET_URL}: {e}")
        raise

    # Initialization Settings
    # to store Websocket response
    context.messages = []
    # to store Sequence 'u' value
    context.last_u = None
    # to store book subscription type: book/book.update
    context.subscription_channel = None
    logging.info(f"--- Starting Scenario: {scenario.name} ---")


def after_scenario(context, scenario):
    # recover original send methods
    if hasattr(context, 'original_ws_send'):
        logging.debug("recover original send methods...")
        context.ws.send = context.original_ws_send
        del context.original_ws_send


    # close Websocket connection
    if hasattr(context, 'ws') and context.ws:
        context.ws.close()
        logging.info("WebSocket Connection closed for scenario.")
    logging.info(f"--- Finished Scenario: {scenario.name} ---")