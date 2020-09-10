# coding: utf-8
import typing
import asyncio
import json
import queue
from starlette.websockets import WebSocket
from .JsPyTextSocket import JsPyTextSocket, JsPyError

__all__ = ['expose', 'callable', 'exclusive_callable', 'clear',
           'is_running', 'get_keys', 'has', 'call_nowait', 'call']

# Function definition called from javascript.
# key:
#   The key name associated with the python function.
# value:
#   [Callable, iscoroutine: bool, is_running: bool, queue.Queue or None]
_exposed_function = {}
# Id number assigned to protocol 'function_call' and 'function'.
_call_id = 0
_CALL_ID_MAX = 0XFFFFFFFF
# Future instance waiting for function_return from clients.
# key: call_id
# value: list of future instance
_call_memory = {}

def expose(key: str, func: typing.Callable, exclusive: bool=False) -> bool:
    """Expose python function to clients by specified key name.

    Bind key name to python function. Enable this python function to be
    called from the client side javascript. The return value of the python
    function is sent to the client.

    Examples in server side
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyFunction

    app = JsMeetsPy()    # Create an application instance.

    def xyz(a, b):
        return [a, b, a+b, None]

    # Bind key name 'abc' to function xyz().
    # Called by the client with this key name.
    JsPyFunction.expose('abc', xyz)

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyFunction.js' in advance.
    retval = await JsPyFunction.call('abc')(1, 2);
    console.log(retval);    // [1,2,3,null]

    Parameters
    ----------
    key: str
        Key name exposing to clients.
        A python function is called from the client via the key name.
        It does not have to be the same as the following function name.
        Of course, it is easier to understand if the key name is the
        same as the function name
    func: Callable
        Python function called via the key name from the client.
        It's a Normal function or async function.
        The return value of the function is limited to a format that
        can be converted into a JSON format as follows.
        Specifiable types:
                int, float, str, True, False, None(convert to null)
                list, dict, tuple(convert to list)
    exclusive: bool, default False
        Whether to run exclusively.
        True:
            Even if many same functions are called asynchronously
            from the clients, they are executed exclusively on a
            first-come, first-served basis.
            This is valid when the exposed python function is async function.
        False:
            It is executed each time it is called from the client.

    Returns
    ----------
    bool
        Successful(True) or unsuccessful(False) to expose.
        Fails if the function already exists and is running.
        If the function already exists and is not currently running,
        you can overwrite it.

    See Also
    ----------
    callable, exclusive_callable
        Another way by decorator.
    """
    global _exposed_function

    if (key in _exposed_function) and _exposed_function[key][2]:
        return False
    _exposed_function[key] = [func,
                              asyncio.iscoroutinefunction(func),
                              False,
                              queue.Queue() if exclusive else None]
    return True

def callable(func: typing.Callable) -> typing.Callable:
    """Decorator that exposes Python functions to clients.

    Bind decorate function name to the python function.
    The effect is the same as expose(func.__name__, func, False)

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyFunction

    app = JsMeetsPy()    # Create an application instance.

    # Same as JsPyFunction.expose('open_function', open_function, False)
    @JsPyFunction.callable
    def open_function(a, b, c):
        return {"a": a, "b": b, "c": c, "all": [a,b,c]}

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyFunction.js' in advance.
    retval = await JsPyFunction.call('open_function')(1, 2, 3);
    console.log(retval);    // {a:1, b:2, c:3, all:[1,2,3]}

    Exceptions
    ----------
    KeyError
        Raise exception when the exposed key name is duplicated.

    See Also
    ----------
    expose()
        Another way by function.
    """
    global _exposed_function

    if func.__name__ not in _exposed_function:
        _exposed_function[func.__name__] = [func,
                                            asyncio.iscoroutinefunction(func),
                                            False,
                                            None]
        return func
    else:
        raise KeyError('The exposed function "{}" is invalid @python'.format(
            func.__name__))

def exclusive_callable(func: typing.Callable) -> typing.Callable:
    """Decorator that exposes Python functions to clients.

    Bind decorate function name to python function.
    The effect is the same as expose(func.__name__, func, True)

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyFunction

    app = JsMeetsPy()    # Create an application instance.

    # Same as JsPyFunction.expose('my_function', my_function, True)
    @JsPyFunction.exclusive_callable
    def my_function():
        return [1, {'a': 2, 'b': 'str'}]

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyFunction.js' in advance.
    retval = await JsPyFunction.call('my_function')();
    console.log(retval);    // [1, {a: 2, b: "str"}]

    Exceptions
    ----------
    KeyError
        Raise Exception when the exposed key name is duplicated.

    See Also
    ----------
    expose()
        Another way by function.
   """
    global _exposed_function

    if func.__name__ not in _exposed_function:
        _exposed_function[func.__name__] = [func,
                                            asyncio.iscoroutinefunction(func),
                                            False,
                                            queue.Queue()]
        return func
    else:
        raise KeyError('The exposed function "{}" is invalid @python'.format(
            func.__name__))

def clear(key: str) -> bool:
    """Clear functions exposed to clients.

    Parameters
    ----------
    key: str
        Key name exposing to clients.
        A python function is called from the client via the key name.

    Returns
    ----------
    bool
        Successful(True) or unsuccessful(False).
        Fails if exposed key name is present but running now.
    """
    global _exposed_function
    if (key in _exposed_function) and (not _exposed_function[key][2]):
        del _exposed_function[key]
        return True
    else:
        return False

def is_running(key: str) -> bool:
    """Get execution status of python function with specified key name.

    Check whether the python function with the specified key name is
    running in the background.

    Parameters
    ----------
    key: str
        Key name exposing to clients.
        A python function is called from the client via the key name.

    Returns
    ----------
    bool
        Now running in the background(True) or not(False).
    """
    global _exposed_function

    if key in _exposed_function:
        return _exposed_function[key][2]
    else:
        return False

def get_keys() -> typing.List[str]:
    """Get key name list of python function exposed to clients.

    Returns
    ----------
    list[str]
        Key name list.
    """
    global _exposed_function

    return list(_exposed_function.keys())

def has(key: str) -> bool:
    """Verification of key name of python function exposed to clients.

    Parameters
    ----------
    key: str
        Key name exposing to clients.
        A python function is called from the client via the key name.

    Parameters
    ----------
    bool
        The key name exists(True) or not(False).
    """
    global _exposed_function

    return(key in _exposed_function)

def call_nowait(key: str,
                target: typing.Union[int,
                                     typing.List[int],
                                     typing.Tuple[int],
                                     typing.Set[int],
                                     None]=None
               ) -> typing.Callable:
    """Execute the javascript function exposed by the client side key name.

    Call client side functions for all connected clients or specified clients.
    The return value or exception from the client is ignored.
    Reaching the client is not guaranteed.
    Simply call the exposed function of the client.

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyFunction

    app = JsMeetsPy()    # Create an application instance.

    # No return, No blocking process
    # No guarantee of reaching the client
    JsPyFunction.call_nowait('abc')(1,2)
        ...

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyFunction.js' in advance.
    function add2(a, b){
        console.log(a);    // 1
        console.log(b);    // 2

        // In call_nowait from server, the return value is ignored.
        return(a+b);
    }

    # Bind key name 'abc' to function add2().
    # Called by the server with this key name.
    JsPyFunction.expose('abc', add2);

    Parameters
    ----------
    key: str
        The key name of the function exposed by the clients.
        A javascript function is called from the server via the key name.
    target: None or int or list or tuple or set, default None
        Specify the socket id of the target client.
        If it does not exist, it is ignored without exception.
        None -> Call all clients currently connected.
        int, list, tuple -> Call to the client with the specified socket id.

    Returns
    ----------
    Callable
        An argument is the data to be sent to the clients.
        Control returns soon.

        Callable Parameters
        ----------
        *args
            Positional argument that can be converted to JSON format.
            Specifiable types:
                int, float, str, None, True, False,
                list, dict, tuple(convert to list)
    """
    def inner_nowait(*args) -> None:
        global _call_id, _CALL_ID_MAX
        nonlocal key, target

        _call_id += 1
        if _call_id > _CALL_ID_MAX:
            _call_id = 1
        this_id = _call_id

        send_dic = {'protocol': 'function', 'key': key,
                    'id': this_id, 'data': args, 'exception': None}
        JsPyTextSocket.reservecast(send_dic, target)
    return inner_nowait

def call(key: str,
         timeout: typing.Union[int, float, None]=0,
         target: typing.Union[int,
                              typing.List[int],
                              typing.Tuple[int],
                              typing.Set[int],
                              None]=None
        ) -> typing.Callable:
    """Execute the javascript function exposed by the client side key name.

    Call client side functions for all connected clients or specified clients.
    Wait for a response from the clients and get the return values or exception.

    Timeout can be set in the argument. Retrieve only the return value
    that responded within the time limit.

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy, JsPyFunction

    app = JsMeetsPy()    # Create an application instance.

    @app.route('/', ['get'])
    async def page_root():
        ...
        ret_values = await JsPyFunction.call('mul2', timeout=2)(5,2)
        # ex) ret_values: {2: [5,2,10], 4: [5,2,10], 6: JsPyError()}
        #    -> Return from socket ID 2,4,6 client within the time limit.
        #       But an exception has occurred on the socket ID 6 client.
        ...

    Examples in client side
    ----------
    // You need to load 'JsPyTextSocket.js' and 'JsPyFunction.js' in advance.
    function mul2(a, b){
        console.log(a);    // 5
        console.log(b);    // 2
        if(Math.random() < 0.1){
            throw "Random exception";
        }
        return([a, b, a*b]);  // [5,2,10]
    }

    # Bind key name 'mul2' to function mul2().
    # Called by the server with this key name.
    JsPyFunction.expose('mul2', mul2);

    Parameters
    ----------
    key: str
        The key name of the function exposed by the clients.
        A javascript function is called from the server via the key name.
    timeout: int or float or None, default None
        Maximum time to wait for a response from the clients.
        If there is a response from all clients within this time, the value
        is returned at that point. If 0 or negative or None, wait indefinitely.
    target: None or int or list or tuple or set, default None
        Specify the socket id of the target client.
        If it does not exist, it is ignored without exception.
        None -> Call all clients currently connected.
        int, list, tuple -> Call to the client with the specified socket id.

    Returns
    ----------
    Async Callable
        An argument is the data to be sent to the clients.
        The await keyword is required to have a return value
        because of an async function.

        Callable Parameters
        ----------
        *args
            Positional argument that can be converted to JSON format.
            Specifiable types:
                int, float, str, None, True, False,
                list, dict, tuple(convert to list)

        Callable Returns
        ----------
        dict
            key:   Socket ID that returned the value within the time limit.
            value: Return value from client. Or JsPyError instance.
                   If an exception occurs in the client side function,
                   it becomes JsPyError instance.

        Callable Raises
        ----------
        TypeError
            Parameter is not JSON serializable.

    Notes
    ----------
    Get only the values returned within the time limit.
    Return values after the time limit are ignored.
    """
    async def inner(*args) -> dict:
        global _call_id, _call_memory, _CALL_ID_MAX
        nonlocal key, timeout, target

        _call_id += 1
        if _call_id > _CALL_ID_MAX:
            _call_id = 1
        this_id = _call_id

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
            return {}
        send_dic = {'protocol': 'function_call', 'key': key,
                    'id': this_id, 'data': args, 'exception': None}
        # Make future in the number of clients
        this_loop = asyncio.get_running_loop()
        this_futures = [this_loop.create_future() for i in target_sockets]
        _call_memory[this_id] = this_futures
        # Send a function call to clients
        JsPyTextSocket.multicast(send_dic, target_sockets)
        # Waiting for a response from clients with timeout
        if (timeout is not None) and (timeout <= 0):
            timeout = None
        done, pending = await asyncio.wait(this_futures, timeout=timeout)
        return_value = {}
        for ft in done:
            try:
                value = ft.result()
                return_value[value[0]] = value[1]
            except JsPyError as e:
                return_value[e.get_socket_id()] = e
        del _call_memory[this_id]
        return return_value
    return inner

def _return_from_js(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'function_return'"""
    global _call_memory

    protocol = dict_data.get('protocol')
    key = dict_data.get('key')
    id = dict_data.get('id')
    data = dict_data.get('data')
    excpt = dict_data.get('exception')
    if isinstance(id, int) and (id in _call_memory):
        for ft in _call_memory[id]:
            if ft.done():
                continue
            else:
                if excpt is not None:
                    ft.set_exception(JsPyError(excpt, protocol, key, id, socket_id))
                else:
                    ft.set_result((socket_id, data))
                break
    # else: ignore

async def _call_from_js(ws: WebSocket, socket_id: int, dict_data: dict) -> None:
    """Processes data with protocol 'function_call' or 'function'"""
    global _exposed_function

    protocol = dict_data.get('protocol')
    key = dict_data.get('key')
    id = dict_data.get('id')
    send_dic = {'protocol': 'function_return', 'key': key, 'id': id,
                'data': None, 'exception': None}
    if (not isinstance(key, str)) or (key not in _exposed_function):
        send_dic['data'] = None
        send_dic['exception'] = 'Function key name is not registered @python'
    else:
        func = _exposed_function[key][0]
        iscoroutine = _exposed_function[key][1]
        isrunning = _exposed_function[key][2]
        exclusive = _exposed_function[key][3]
        if exclusive and isrunning:
            this_loop = asyncio.get_running_loop()
            this_future = this_loop.create_future()
            exclusive.put_nowait(this_future)
            # Since it is an exclusive execution function,
            # it makes a reservation in the waiting list and waits in order.
            await this_future

        _exposed_function[key][2] = True    # function running
        # Start of function call
        await asyncio.sleep(0)
        if iscoroutine:
            try:
                send_dic['data'] = await func(*dict_data.get('data'))
            except Exception as e:
                send_dic['data'] = None
                send_dic['exception'] = str(e) + ' @python'
        else:
            try:
                send_dic['data'] = func(*dict_data.get('data'))
            except Exception as e:
                send_dic['data'] = None
                send_dic['exception'] = str(e) + ' @python'
        await asyncio.sleep(0)
        # End of function call
        _exposed_function[key][2] = False   # function not running
        if exclusive and (not exclusive.empty()):
            exclusive.get_nowait().set_result(True)
            _exposed_function[key][2] = True    # soon running
    if protocol == 'function_call':
        try:
            send_text = json.dumps(send_dic)
        except Exception as e:
            send_dic['exception'] = str(e) + ' @python'
            send_dic['data'] = None
            send_text = json.dumps(send_dic)
        await ws.send_text(send_text)
    # elif protocol == 'function':  Not return to client

JsPyTextSocket.add_protocol('function_return', _return_from_js)
JsPyTextSocket.add_protocol('function_call', _call_from_js)
JsPyTextSocket.add_protocol('function', _call_from_js)
