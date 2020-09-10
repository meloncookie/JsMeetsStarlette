# coding: utf-8
import typing
import json
import asyncio
from collections import deque
from starlette.websockets import WebSocket
from .JsPyTextSocket import JsPyTextSocket, JsPyError
from . import JsPyBackground

__all__ = ['push_nowait', 'push', 'pop', 'shift', 'add_callback',
           'clear_callback', 'is_empty', 'get_keys',
           'has', 'clear', 'clear_all', 'remove', 'remove_all']

# Queue data pool
# key:   name of queue
# value: queue data (collections.deque object)
_queue_stack = {}
# Id number assigned to protocol 'queue' and 'queue_call'
_queue_id = 0
_QUEUE_ID_MAX = 0XFFFFFFFF
# Future instance waiting for queue_return from clients.
# key:   queue_id
# value: list of future instance
_queue_memory = {}
# Callback function called every time Queue data arrives from client.
# Normal function or async function.
# Function has one argument. It is the key name of the queue that arrived.
_queue_callbacks = set()

def push_nowait(key: str,
                target: typing.Union[int,
                                     typing.List[int],
                                     typing.Tuple[int],
                                     typing.Set[int],
                                     None]=None
               ) -> typing.Callable:
    """Send data to the queue of the connected clients.

    Send data to all connected clients or specified clients,
    but does not guarantee arrival.
    The sent data is stored in the client queue corresponding to the key name.

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyQueue

    app = JsMeetsPy()    # Create an application instance.

    @app.route('/', ['get'])
    def page_root():
        ...
        # Send data to all connected clients.
        JsPyQueue.push_nowait('stack1')({'a': [1,2,[2,3]], 'b': True})
        JsPyQueue.push_nowait('stack1')(10)
        JsPyQueue.push_nowait('stack2')(None)
        # Send data to socket ID 2 & 5 only.
        # If socket ID does not exist, it is ignored.
        JsPyQueue.push_nowait('stack2', [2, 5])([True, False])
        ...

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyQueue.js' in advance.
    // Operations on queue key name 'stack1'
    if(!JsPyQueue.is_empty('stack1')){
        // undefined is returned if there is no data on the stack1.
        pop_data1 = JsPyQueue.pop('stack1');
    }

    // Operations on queue key name 'stack2'
    pop_data2 = JsPyQueue.shift('stack2');

    Parameters
    ----------
    key: str
        The name that identifies the client side queue.
        It has an independent queue for each key name.
    target: None or int or list or tuple or set, default None
        Specify the socket id of the target client.
        If it does not exist, it is ignored without exception.
        None -> Call all clients currently connected.
        int, list, tuple -> Call to the client with the specified socket id.

    Returns
    ----------
    Callable
        The argument is the data stored in the queue of the client.
        Control returns soon.

        Callable Parameters
        ----------
        data:
            Data stored in the client side queue.
            The data can be converted to a JSON format as follows.

            Specifiable types:
                    int, float, str, True, False, None(convert to null)
                    list, dict, tuple(convert to list)
    """
    def inner_nowait(data) -> None:
        global _queue_id, _QUEUE_ID_MAX
        nonlocal key, target

        _queue_id += 1
        if _queue_id > _QUEUE_ID_MAX:
            _queue_id = 1
        this_id = _queue_id
        if this_id > _QUEUE_ID_MAX:
            this_id = 1

        send_dic = {'protocol': 'queue', 'key': key,
                    'id': this_id, 'data': data, 'exception': None}
        # Send a queue call to clients
        JsPyTextSocket.reservecast(send_dic, target)
    return inner_nowait

def push(key: str,
         timeout: typing.Union[int, float, None]=0,
         target: typing.Union[int,
                              typing.List[int],
                              typing.Tuple[int],
                              typing.Set[int],
                              None]=None
        ) -> typing.Callable:
    """Send data to the queue of the connected clients.

    Send data to all connected clients or specified clients
    and confirm that the data has been delivered.
    The sent data is stored in the client queue corresponding
    to the key name.

    Examples in python side
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyQueue

    app = JsMeetsPy()    # Create an application instance.

    @app.route('/', ['get'])
    async def page_root():
        ...
        # Wait for a data acknowledgment from the clients.
        receive_clients = await JsPyQueue.push(
            'stack1', timeout=2)({'a': [1,2,[2,3]], 'b': True})
        # ex) receive_clients = [2, 3, 5]
        #     Socket ID that could be sent reliably are 2, 3, 5.

    Parameters
    ----------
    key: str
        The name that identifies the client side queue.
        It has an independent queue for each key name and stacks data.
    timeout: float or None, default None
        Maximum time to wait for acknowledgment from clients.
        If 0 or negative or None, wait indefinitely.
    target: None or int or list or tuple or set, default None
        Specify the socket id of the target client.
        If it does not exist, it is ignored without exception.
        None -> Call all clients currently connected.
        int, list, tuple -> Call to the client with the specified socket id.

    Returns
    ----------
    Async Callable
        The argument is the data stored in the queue of the client.
        The await keyword is required to have a return value
        because of an async function.

        Callable Parameters
        ----------
        data:
            Data stored in the client side queue.
            The data can be converted to a JSON format as follows.

            Specifiable types:
                    int, float, str, True, False, None(convert to null)
                    list, dict, tuple(convert to list)

        Callable Returns
        ----------
        list
            List of the socket ID received a response within the time limit.
            The socket ID is a unique number that is assigned to the client
            by the server when websocket communication is established.

        Callable Raises
        ----------
        TypeError
            Parameter is not JSON serializable.
    """
    async def inner(data) -> list:
        global _queue_id, _QUEUE_ID_MAX, _queue_memory
        nonlocal key, timeout, target

        _queue_id += 1
        if _queue_id > _QUEUE_ID_MAX:
            _queue_id = 1
        this_id = _queue_id

        target_sockets = []
        if target is None:
            target_sockets = JsPyTextSocket.get_socket_id()
        elif isinstance(target, int):
            all_sockets = JsPyTextSocket.get_socket_id()
            if target in all_sockets:
                target_sockets = [target]
        elif isinstance(target, (tuple, list, set)):
            all_sockets = JsPyTextSocket.get_socket_id()
            target_sockets = [i for i in target if (i in all_sockets)]

        # There is no specified client.
        if len(target_sockets) == 0:
            return []
        send_dic = {'protocol': 'queue_call', 'key': key,
                    'id': this_id, 'data': data, 'exception': None}

        # Make future in the number of clients
        this_loop = asyncio.get_running_loop()
        this_futures = [this_loop.create_future() for i in target_sockets]
        _queue_memory[this_id] = this_futures
        # Send a queue call to clients
        JsPyTextSocket.multicast(send_dic, target_sockets)
        # Waiting for a response from clients with timeout
        if (timeout is not None) and (timeout <= 0):
            timeout = None
        done, pending = await asyncio.wait(this_futures, timeout=timeout)
        return_value = []
        for ft in done:
            try:
                return_value.append(ft.result())
            except:
                pass
        del _queue_memory[this_id]
        return return_value
    return inner

def pop(key: str, default_value=None):
    """Remove and return an element from the right side of the queue.(LIFO)

    Data is sent from the client in pairs with the key name.
    The received data is stored in the server queue corresponding to key name.
    Remove and return an element from the right side of the queue.
    If the queue corresponding to the key name is empty or not present,
    the default value specified in the parameter is returned.

    Parameters
    ----------
    key: str
        The name that identifies the server side queue.
        It has an independent queue for each key name.
    default_value: Any, Default None
        Return value when there is no valid queue data.
        (Empty or No queue key name)

    See Also
    ----------
    shift()
    """
    global _queue_stack
    if key in _queue_stack:
        return(_queue_stack[key].pop()
               if len(_queue_stack[key])
               else default_value)
    else:
        return default_value

def shift(key: str, default_value=None):
    """Remove and return an element from the left side of the queue.(FIFO)

    Data is sent from the client in pairs with the key name.
    The received data is stored in the server queue corresponding to key name.
    Remove and return an element from the left side of the queue.
    If the queue corresponding to the key name is empty or not present,
    the default value specified in the parameter is returned.

    Parameters
    ----------
    key: str
        The name that identifies the server side queue.
        It has an independent queue for each key name.
    default_value: Any, Default None
        Return value when there is no valid queue data.
        (Empty or No queue key name)

    See Also
    ----------
    pop()
    """
    global _queue_stack
    if key in _queue_stack:
        return(_queue_stack[key].popleft()
               if len(_queue_stack[key])
               else default_value)
    else:
        return default_value

def add_callback(func: typing.Callable) -> None:
    """Register the callback function when data arrives in the server queue.

    When the queue data is sent from the client to the server,
    the registration functions are called.

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyQueue

    app = JsMeetsPy()    # Create an application instance.

    def qprint(come_key):
        print("Queue key {}, value: {} has come.".format(
              come_key, JsPyQueue.pop(come_key)))
    async def qbroadcast(come_key):
        if come_key == 'cast':
            x = JsPyQueue.pop(come_key)
            await JsPyQueue.push_nowait('message')(x)

    JsPyQueue.add_callback(qprint)
    JsPyQueue.add_callback(qbroadcast)

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyQueue.js' in advance.
    // Send character string to server queue key name 'greeting'.
    JsPyQueue.push_nowait('cast')('Hello everyone')

    Parameters
    ----------
    func: Callable
        Function have one argument. It is the queue key name of the destination.
        Normal function or coroutine function.

    See Also
    ----------
    clear_callback()
    """
    global _queue_callbacks
    _queue_callbacks.add(func)

def clear_callback() -> None:
    """Clear all callback functions when data arrives in the server queue.

    See Also
    ----------
    add_callback()
    """
    global _queue_callbacks
    _queue_callbacks.clear()

def is_empty(key: str) -> bool:
    """Whether data is empty in the queue with the key name.

    Parameters
    ----------
    key: str
        The name that identifies the server side queue.
        It has an independent queue for each key name.

    Returns
    ----------
    bool
        True(not exit key name or empty), False(not empty)
    """
    global _queue_stack
    if key in _queue_stack:
        return(len(_queue_stack[key]) == 0)
    else:
        return True

def get_keys() -> typing.List[str]:
    """Get a list of all key names that exist in the server queue.

    Returns
    ----------
    list
    """
    global _queue_stack
    return list(_queue_stack.keys())

def has(key: str) -> bool:
    """Whether a server queue with the specified key name exists.

    The queue key name does not disappear when the queue is emptied.
    Use the remove() function to delete the key name of an existing queue.

    Parameters
    ----------
    key: str
        The name that identifies the server side queue.
        It has an independent queue for each key name.

    Returns
    ----------
    bool
        True(exist), False(not exist)
    """
    global _queue_stack
    return key in _queue_stack

def clear(key: str) -> None:
    """Clear the inventory data of the server queue with the key name.

    Empty the data of the queue with the specified key name.
    The queue with the specified key name survives.

    Parameters
    ----------
    key: str
        The name that identifies the server side queue.
        It has an independent queue for each key name.

    See Also
    ----------
    clear_all(), remove(), remove_all()
    """
    global _queue_stack
    if key in _queue_stack:
        _queue_stack[key].clear()

def clear_all() -> None:
    """Clear the inventory data of the all server queue.

    Empty the data of the queue with the all key name.
    The queue with the all key name survives.

    See Also
    ----------
    clear(), remove(), remove_all()
    """
    global _queue_stack
    for key in _queue_stack:
        _queue_stack[key].clear()

def remove(key: str) -> None:
    """Delete server queue with the specified key name.

    Delete the key name of the existing queue along with the data.

    See Also
    ----------
    clear(), clear_all(), remove_all()
    """
    global _queue_stack
    if key in _queue_stack:
        del _queue_stack[key]

def remove_all() -> None:
    """Delete all server queue.

    Delete all key name of the existing queue along with the data.

    See Also
    ----------
    clear(), clear_all(), remove()
    """
    global _queue_stack
    _queue_stack.clear()

async def _queue(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'queue', 'queue_call'"""
    global _queue_stack, _queue_callbacks

    key = dict_data.get('key')
    data = dict_data.get('data')
    id = dict_data.get('id')
    send_dic = {'protocol': 'queue_return', 'key': key, 'id': id,
                'data': None, 'exception': None}
    try:
        if key in _queue_stack:
            _queue_stack[key].append(data)
        else:
            _queue_stack[key] = deque([data])
    except:
        send_dic['exception'] = 'The queue key name is incorrect @python'
        if dict_data.get('protocol') == 'queue_call':
            await ws.send_json(send_dic)
    else:
        for callback in _queue_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(key))
                else:
                    JsPyBackground.register_function(callback, (key,))
            except:
                pass
        if dict_data.get('protocol') == 'queue_call':
            await ws.send_json(send_dic)

def _queue_return(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'queue_return'"""
    global _queue_memory

    id = dict_data.get('id')
    exception = dict_data.get('exception')
    if isinstance(id, int) and (id in _queue_memory):
        for ft in _queue_memory[id]:
            if ft.done():
                continue
            else:
                if not exception:
                    ft.set_result(socket_id)
                else:
                    ft.set_exception(exception)
                break

JsPyTextSocket.add_protocol('queue', _queue)
JsPyTextSocket.add_protocol('queue_call', _queue)
JsPyTextSocket.add_protocol('queue_return', _queue_return)
