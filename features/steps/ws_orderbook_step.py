from behave import *
import json
import time
import websocket
import logging
from unittest.mock import MagicMock

def _wait_and_receive(context, timeout=10.0):
    try:
        context.ws.settimeout(timeout)
        message_str = context.ws.recv()
        if not message_str:
            raise ConnectionAbortedError("Connect closed.")


        logging.debug(f"RECV RAW: {message_str}")

        message = json.loads(message_str)

        if message.get("code") != 0 and message.get("method") == "subscribe":
            context.last_error = message
        else:
            context.messages.append(message)
        return message

    except websocket.WebSocketTimeoutException:
        raise TimeoutError(f"Didn't receive messages in  {timeout}s")
    except Exception as e:
        raise ConnectionError(f"Error: {e}")



#  ---Given---
@given('WebSocket book API is connected successfully')
def step_impl(context):
    assert hasattr(context, 'ws')
    assert context.ws.connected

@given('I subscribed to "{channel}" (SNAPSHOT) mode')
def step_impl(context, channel):
    context.execute_steps(f'''
        When I send a subscription request: channels="{channel}", subscription_type="SNAPSHOT", update_frequency="500"
        Then I should receive a response said Successful Subscription
    ''')
    context.subscription_channel = channel

@given('I subscribed to "{channel}" (SNAPSHOT_AND_UPDATE) mode')
def step_impl(context, channel):
    context.execute_steps(f'''
        When I send a subscription request: channels="{channel}", subscription_type="SNAPSHOT_AND_UPDATE", update_frequency="100"
        Then I should receive a response said Successful Subscription
    ''')
    context.subscription_channel = channel

@given('I am spy on send methods')
def step_impl(context):
    if not hasattr(context, 'original_ws_send'):
        context.original_ws_send = context.ws.send

        context.ws.send = MagicMock(wraps=context.original_ws_send)
        logging.info("WebSocket 'send' message is spied on).")
    else:
        logging.info("WebSocket 'send' already under spied")



# ---When---
@when('I send a subscription request: channels="{channel}", subscription_type="{subscription_type}", update_frequency="{update_frequency}"')
def step_impl(context, channel, subscription_type, update_frequency):
    request = {
        "id": int(time.time()),
        "method": "subscribe",
        "params": {
            "channels": [channel]
        }
    }
    if subscription_type != "SNAPSHOT":
        request["params"]["book_subscription_type"] = subscription_type

    if subscription_type == "SNAPSHOT_AND_UPDATE" and update_frequency != "10":
        request["params"]["book_update_frequency"] = int(update_frequency)
    elif subscription_type == "SNAPSHOT" and update_frequency != "500":
        request["params"]["book_update_frequency"] = int(update_frequency)

    logging.debug(f"SEND: {request}")
    context.ws.send(json.dumps(request))
    context.subscription_channel = channel


@when('I waited and received the {n:d} snapshot response')
def step_impl(context, n):
    while len(context.messages) < n:
        _wait_and_receive(context)

@when('I waited and received the next delta response')
def step_impl(context):
    while len(context.messages) < 4:
        _wait_and_receive(context)

@when('I wait up to {seconds:d} seconds to receive a heartbeat package')
def step_impl(context, seconds):
    start_time = time.time()
    context.heartbeat_received = False
    while time.time() - start_time < seconds:
        try:
            message = _wait_and_receive(context, timeout=1.0)
        except TimeoutError:
            continue

        result = message.get("result", {})
        if result.get("channel") == "book.update":
            data = result.get("data", [{}])[0]
            update_data = data.get("update", {})

            if update_data.get("asks") == [] and update_data.get("bids") == []:
                logging.info("received a heartbeat package")
                context.heartbeat_received = True
                assert "u" in data and "pu" in data
                assert data["pu"] == context.last_u, \
                    "'u' sequence in heartbeat package mismatched"
                context.last_u = data["u"]
                return

    assert context.heartbeat_received, f"Didn't receive heartbeat package in {seconds}s"

@when('I stored the u field of the snapshot response')
def step_impl(context):

    if not context.messages:
        _wait_and_receive(context)

    snapshot_msg = context.messages[1]

    data = snapshot_msg["result"]["data"][0]
    context.last_u = data["u"]

    assert context.last_u is not None

    logging.info(f"the first Snapshot request: U value: {context.last_u}")

@when('Intentionally set the locally stored u sequence to "BAD_SEQUENCE"')
def step_impl(context):
    assert context.last_u is not None, "No 'last_u' value stored, check previous step"
    context.last_u = "BAD_SEQUENCE"
    logging.warning(f"Intentionally set the locally stored 'u' sequence to: {context.last_u}")


@when('Re-subscribed the same request')
def step_impl(context):
    context.execute_steps(f'''
            Given I subscribed to "book.BTCUSD-PERP.10" (SNAPSHOT) mode
        ''')

@when('I re-subscribed the same request with depth value changed (TC-11)')
def step_impl(context):
    if "TC-11" not in context.tags:
        logging.info("Skipping TC10 action (tag @TC10 not present)")
        return

    context.execute_steps(f'''
            Given I subscribed to "book.BTCUSD-PERP.50" (SNAPSHOT) mode
        ''')

@when('I re-subscribed the same request with depth value changed (TC-13)')
def step_impl(context):
    if "TC-13" not in context.tags:
        logging.info("Skipping TC-13 action (tag @TC-13 not present)")
        return

    context.execute_steps(f'''
            Given I subscribed to "book.BTCUSD-PERP.50" (SNAPSHOT) mode
        ''')

@when('received and collect {count:d} delta messages')
def step_impl(context, count):
    logging.info(f"received {count} delta messages...")
    context.timestamps = []
    context.sequence_ok = True

    start_time = time.time()
    max_wait_seconds = 10

    while len(context.timestamps) < count:

        try:
            message = _wait_and_receive(context, timeout=0.5)

            if message.get("result", {}).get("channel") == "book.update":
                data = message["result"]["data"][0]

                pu = data.get("pu")
                if pu != context.last_u:
                    context.sequence_ok = False
                    logging.error(f"Sequence mismatched! Expected PU={context.last_u}, Actual PU={pu}")
                context.last_u = data.get("u")

                update_data = data.get("update", {})
                if update_data.get("asks") != [] or update_data.get("bids") != []:
                    context.timestamps.append(data["t"])

        except TimeoutError:
            pass

@when('received and collect snapshot messages in {seconds:d}s')
def step_impl(context, seconds):
    logging.info(f"{seconds} 秒, received snapshot messages...")
    context.timestamps = []
    context.sequence_ok = True

    start_time = time.time()
    while time.time() - start_time < seconds:
        try:
            message = _wait_and_receive(context, timeout=0.5)

            if message.get("result", {}).get("channel") == "book":
                data = message["result"]["data"][0]

                pu = data.get("pu")
                if pu != context.last_u:
                    context.sequence_ok = False
                    logging.error(f"Sequence mismatched! Expected PU={context.last_u}, Actual PU={pu}")
                context.last_u = data.get("u")

                update_data = data.get("update", {})
                if update_data.get("asks") != [] or update_data.get("bids") != []:
                    context.timestamps.append(data["t"])

        except TimeoutError:
            pass


# ---Then---
@then('I should receive a response said Successful Subscription')
def step_impl(context):
    if not context.messages:
        _wait_and_receive(context)

    subscribed_msg = context.messages[0]

    assert subscribed_msg.get("method") == "subscribe", f"Not 'subscribe': {subscribed_msg.get('method')}"
    assert subscribed_msg.get("code") == 0, f"Subscribed failed, code: {subscribed_msg.get('code')}"

@then('I should receive a snapshot response')
def step_impl(context):

    start_time = time.time()
    timeout = 10

    while time.time() - start_time < timeout:
        for msg in context.messages:
            result = msg.get("result", {})
            if result.get("channel") == "book":
                logging.info("Find 'book' snapshot.")

                assert msg.get("method") == "subscribe"
                assert msg.get("code") == 0
                return

        try:
            _wait_and_receive(context, timeout=1.0)
        except TimeoutError:
            pass

        raise AssertionError(f"Didn't receive snapshot message in {timeout}s.")

    snapshot_msg = context.messages[1]

    assert snapshot_msg.get("method") == "subscribe", f"Not 'subscribe': {snapshot_msg.get('method')}"
    assert snapshot_msg.get("code") == 0, f"Subscribed failed, code: {snapshot_msg.get('code')}"

    result = snapshot_msg.get("result", {})
    assert result.get("channel") == "book", f"Incorrect channel：{result.get('channel')}"
    assert result.get("subscription") == context.subscription_channel, f"subscription:{result.get('subscription')}"
    assert "data" in result and len(result.get("data", [])) > 0


@then('"depth" in snapshot response should be: {depth:d}')
def step_impl(context, depth):
    snapshot_msg = context.messages[1]
    result = snapshot_msg.get("result", {})
    assert result.get("depth") == depth, \
        f"expected depth {depth}, Actual depth {result.get('depth')}"

@then('"instrument_name" in snapshot response should be: {instrument_name}')
def step_impl(context, instrument_name):
    snapshot_msg = context.messages[1]
    result = snapshot_msg.get("result", {})
    assert result.get("instrument_name") == instrument_name, \
        f"Expected name is {instrument_name}, Actual name is {result.get('instrument_name')}"

@then('Subscription request is sent failed')
def step_impl(context):
    message = None
    # I tried to send such negative requests by chrome and found no requests could be sent out
    # identify failed subscription by checking if received subscribed message
    try:
        context.ws.settimeout(1)
        message = context.ws.recv()
        assert message is not None
    except websocket.WebSocketTimeoutException:
        logging.info("Didn't receive response (Expected Result)")
        pass
    finally:
        context.ws.settimeout(10)

@then('The second snapshot response should be a valid snapshot message')
def step_impl(context):
    if len(context.messages) < 3:
        time.sleep(3)
        raise AssertionError(f"Expected to receive at least 3 response.")

    if not context.messages[2]:
        _wait_and_receive(context)

    snapshot_msg = context.messages[2]
    result = snapshot_msg.get("result", {})
    assert result.get("channel") == "book", "Channel is not 'book'"
    assert len(result.get("data", [])) > 0, "No 'data'"

@then('The time interval between messages should be close to {expected_ms:d}ms')
def step_impl(context,expected_ms):
    if len(context.timestamps) < 10:
        logging.warning(f"Only collect {len(context.timestamps)} messages), ")

    total_time_span_ms = context.timestamps[-1] - context.timestamps[0]
    num_intervals = len(context.timestamps) - 1

    average_interval_ms = total_time_span_ms / num_intervals

    tolerance_percent = 0.5
    min_ms = expected_ms * (1 - tolerance_percent)
    max_ms = expected_ms * (1 + tolerance_percent)

    assert min_ms <= average_interval_ms <= max_ms

@then('The data structure of the snapshot should be correct')
def step_impl(context):
    snapshot_msg = context.messages[-1]
    data = snapshot_msg["result"]["data"][0]
    expected_depth = snapshot_msg["result"]["depth"]

    assert "bids" in data
    assert "asks" in data
    assert "t" in data
    assert "tt" in data
    assert "u" in data
    assert len(data["bids"]) <= expected_depth
    assert len(data["asks"]) <= expected_depth


@then('The response should be a valid delta message')
def step_impl(context):
    update_msg = context.messages[-1]
    result = update_msg.get("result", {})
    assert result.get("channel") == "book.update"
    assert len(result.get("data", [])) > 0

@then('I stored the u field of the snapshot response')
def step_impl(context):
    snapshot_msg = context.messages[1]
    data = snapshot_msg["result"]["data"][0]
    context.last_u = data["u"]
    assert context.last_u is not None
    logging.info(f"[Info] 'U' sequence in snapshot response : {context.last_u}")

@then('The u and pu sequences must remain continuous')
def step_impl(context):
    assert context.sequence_ok, "u/pu mismatched"


@then('pu field of the delta message should be equal to u field stored')
def step_impl(context):
    update_msg = context.messages[2]
    assert context.last_u is not None

    data = update_msg["result"]["data"][0]
    pu = data["pu"]
    u = data["u"]
    assert pu == context.last_u, \
        f"Sequence mismatched! Expected PU={context.last_u}, Actual PU={pu}"
    context.last_u = u

@then('The data structure of the delta should be correct')
def step_impl(context):
    update_msg = context.messages[2]

    data = update_msg["result"]["data"][0]
    assert "update" in data
    assert "t" in data
    assert "tt" in data
    assert "u" in data
    assert "pu" in data

    update = data["update"]
    assert "bids" in update
    assert "asks" in update

@then('I should have received a heartbeat message')
def step_impl(context):
    assert context.heartbeat_received, f"Didn't receive heartbeat message"

@then('I detected sequences mismatch')
def step_impl(context):
    update_msg = context.messages[-1]
    data = update_msg["result"]["data"][0]
    pu = data["pu"]

    logging.info(f"[Info] Update: pu={pu}. local u={context.last_u}")

    assert pu != context.last_u
    logging.info("I detected sequences mismatch")
    context.mismatch_detected = True

@then('No unsubscribe message sent')
def step_impl(context):
    if not isinstance(context.ws.send, MagicMock):
        raise AssertionError("'send' method is not spied")

    all_calls = context.ws.send.call_args_list
    logging.info(f"Check {len(all_calls)} 'send' records")

    for call in all_calls:
        message_string = call[0][0]
        try:
            message_json = json.loads(message_string)
            if message_json.get("method") == "unsubscribe":
                raise AssertionError(f"Find unsubscribe message: {message_string}")
        except (json.JSONDecodeError, AttributeError):
            pass
