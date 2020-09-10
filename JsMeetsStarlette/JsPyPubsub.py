# coding: utf-8
import typing
import json
import asyncio
from starlette.websockets import WebSocket
from .JsPyTextSocket import JsPyTextSocket, JsPyError
from . import JsPyBackground

__all__ = ['subscribe', 'unsubscribe', 'publish']

# Id number assigned to 'pub'.
_pubsub_id = 0
_PUBSUB_ID_MAX = 0xFFFFFFFF
# Management ledger of subscribed client IDs for topics.
# key:   name of topic
# value: Set of subscribed socket ID
_topic_manager = {}
# Server callback function ledger for topic.
# key:   name of topic
# value: Callback function
_topic_callback = {}

def subscribe(topic: str, func: typing.Callable=None):
    """Make a subscription reservation on the server side subscriber.

    Make a subscription reservation for the topic name on the server side.
    When message with this topic is published, the registration callback
    function is called. Exceptions that occur within the callback function
    are ignored.

    You can register one callback function for one topic.
    There are two ways to register a callback function.
    One is a decorator method, the other is a function method.

    Examples1
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyPubsub

    app = JsMeetsPy()    # Create an application instance.

    @JsPyPubsub.subscribe('topic1')
    def topic_callback(topic, data):
        ...

    Examples2
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyPubsub

    app = JsMeetsPy()    # Create an application instance.

    def topic_callback(topic, data):
        ...

    JsPyPubsub.subscribe('topic1', topic_callback)

    Parameters
    ----------
    topic: str
        Topic name to subscribe.
    func: Callable
        Callbak function when the argument topic message is published.
        It has two arguments. The first argument is the topic name and
        the second argument is the topic data.

    Returns
    ----------
    True
    """
    global _topic_callback
    if func is None:
        def inner(target_func: typing.Callable) -> None:
            global _topic_callback
            nonlocal topic
            _topic_callback[topic] = target_func
        return inner
    else:
        _topic_callback[topic] = func
        return True

def unsubscribe(topic: str):
    """Cancel a subscription reservation on the server side subscriber.

    Parameters
    ----------
    topic: str
        Topic name to unsubscribe.

    Returns
    ----------
    True
    """
    global _topic_callback
    if topic in _topic_callback:
        del _topic_callback[topic]
    return True

def publish(topic: str, suppress: bool=False) -> typing.Callable:
    """Publish the message associated with the topic name.

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyPubsub

    app = JsMeetsPy()    # Create an application instance.

    def some_function():
        ...
        JsPyPubsub.publish('target_topic', True)({'a': 1, 'b': [1, 2]})
        ...

    @JsPyPubsub.subscribe('target_topic')
    def hoge(topic, data):
        # Publish from the server with parameter suppress=True,
        # then can't subscribe on myself(=server side subscriber).
        print(data)

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyPubsub.js' in advance.
    function print_sub(topic, data){
        console.log(data);    // {a: 1, b: [1, 2]}
    }
    JsPyPubsub.subscribe("target_topic", print_sub);

    Parameters
    ----------
    topic: str
        Topic name to publish.
    suppress: bool, default False
        The published message is sent to the server's broker.
        Distributed from the broker to the subscriber.
        True : Suppress the distribution of data from broker to myself.
        False: Not suppress

    Returns
    ----------
    Callable

        Callable Parameters
        ----------
        message
            The published message that can be converted to JSON format.
            Specifiable types:
                int, float, str, None, True, False,
                list, dict, tuple(convert to list)

        Callable returns
        ----------
        True
    """
    def inner(message) -> bool:
        global _topic_manager, _topic_callback, _pubsub_id, _PUBSUB_ID_MAX
        nonlocal topic, suppress
        _pubsub_id += 1
        if _pubsub_id > _PUBSUB_ID_MAX:
            _pubsub_id = 1
        send_dic = {'protocol': 'pub', 'key': topic, 'id': _pubsub_id,
                    'data': message, 'exception': None}
        # from broker to server side subscriber
        if (suppress is False) and (topic in _topic_callback):
            JsPyBackground.register_function(
                _topic_callback[topic], (topic, message))
        # from broker to client side subscriber
        if topic in _topic_manager:
            # Data transmission is not guaranteed.
            JsPyTextSocket.reservecast(send_dic, _topic_manager[topic])
        return(True)
    return inner

def get_topics() -> typing.List[str]:
    """Get a list of all subscribed topic name.

    Returns
    ----------
    typing.List[str]
    """
    global _topic_callback
    return list(_topic_callback.keys())


def _sub_from_js(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'sub_call'"""
    global _topic_manager
    topic = dict_data.get('key')
    send_dic = {'protocol': 'sub_return', 'key': topic, 'id': dict_data['id'],
                'data': None, 'exception': None}
    try:
        if topic in _topic_manager:
            _topic_manager[topic].add(socket_id)
        else:
            _topic_manager[topic] = set([socket_id])
    except:
        send_dic['exception'] = 'The topic name is incorrect @python'
    asyncio.create_task(ws.send_json(send_dic))

def _unsub_from_js(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'unsub_call'"""
    global _topic_manager
    topic = dict_data.get('key')
    send_dic = {'protocol': 'unsub_return', 'key': topic, 'id': dict_data['id'],
                'data': None, 'exception': None}
    try:
        if topic in _topic_manager:
            _topic_manager[topic].discard(socket_id)
            if not _topic_manager[topic]:
                del _topic_manager[topic]
    except:
        send_dic['exception'] = 'The topic name is incorrect @python'
    asyncio.create_task(ws.send_json(send_dic))

def _pub_from_js(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'pub_call'"""
    global _topic_manager, _topic_callback, _pubsub_id, _PUBSUB_ID_MAX
    topic = dict_data['key']
    suppress = dict_data['exception']
    message = dict_data['data']
    send_dic = {'protocol': 'pub_return', 'key': topic,
                'id': dict_data['id'], 'data': None, 'exception': None}
    asyncio.create_task(ws.send_json(send_dic))
    _pubsub_id += 1
    if _pubsub_id > _PUBSUB_ID_MAX:
        _pubsub_id = 1
    # from broker to server side subscriber
    try:
        if topic in _topic_callback:
            if asyncio.iscoroutinefunction(_topic_callback[topic]):
                asyncio.create_task(_topic_callback[topic](topic, message))
            else:
                _topic_callback[topic](topic, message)
    except:
        pass
    # from broker to client side subscriber
    send_dic = {'protocol': 'pub', 'key': topic, 'id': _pubsub_id,
                'data': message, 'exception': None}
    try:
        if topic in _topic_manager:
            if suppress is False:
                JsPyTextSocket.multicast(send_dic, _topic_manager[topic])
            else:
                JsPyTextSocket.multicast(send_dic,
                    _topic_manager[topic]-{socket_id})
    except:
        pass

JsPyTextSocket.add_protocol('sub_call', _sub_from_js)
JsPyTextSocket.add_protocol('unsub_call', _unsub_from_js)
JsPyTextSocket.add_protocol('pub_call', _pub_from_js)

def _socket_event(socket_id: int, event: str):
    """When the web socket is closed, remove the socket ID
    from the topic manager."""
    global _topic_manager
    if event == 'disconnect':
        for topic in _topic_manager:
            _topic_manager[topic].discard(socket_id)
            if not _topic_manager[topic]:
                del _topic_manager[topic]

JsPyTextSocket.add_socket_event(_socket_event)
