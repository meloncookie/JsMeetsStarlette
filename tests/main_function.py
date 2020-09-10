import typing
import asyncio
import json
from starlette.responses import PlainTextResponse
from JsMeetsStarlette import JsMeetsPy, JsPyError, JsPyTextSocket, JsPyFunction

# Access http://xxx/static/index_function.html
app = JsMeetsPy(debug=True, static='static',
                templates='templates')

@JsPyFunction.callable
async def py_normal(title: str):
    """Normal exposed function

    Enter -> async sleep 10sec -> Exit
    Respond to calls from other clients, even if the call is from one client.

    Parameters
    ----------
    title: str
        Characters to print out on the server

    Returns
    ----------
    True
    """
    print(f'Enter py_normal: {title}')
    await asyncio.sleep(10)
    print(f'Exit  py_normal: {title}')
    return True

@JsPyFunction.exclusive_callable
async def py_exclusive(title: str):
    """Exclusive exposed function

    Enter -> async sleep 10sec -> Exit
    During the call from one client,
    the call from another client is made to wait.

    Parameters
    ----------
    title: str
        Characters to print out on the server

    Returns
    ----------
    True
    """
    print(f'Enter py_exclusive: {title}')
    await asyncio.sleep(10)
    print(f'Exit  py_exclusive: {title}')
    return True

def positive_sum3(a: int, b: int, c: int=0):
    """Normal exposed function

    Parameters
    ----------
    a: int
    b: int
    c: int, default 0
        All parameters are positive values.
        If negative, an exception is raised.

    Returns
    ----------
    int
    """
    if a<0 or b<0 or c<0:
        raise Exception('Error: Negative argument')
    return a+b+c
JsPyFunction.expose('py_sum', positive_sum3)

@JsPyFunction.callable
async def reverse_call(name:str, key:str, args:list):
    """Call various server functions from the client side.

    Parameters
    ----------
    name: str
        function name
    key: str
        Key name used for call_nowait(key)(*args), call(key)(*args)
    args: list
        parameter list of function

    Return
    ----------
    Any
    """
    if name == 'get_socket_id':
        # Get a tuple of currently connected socket ID.
        return JsPyTextSocket.get_socket_id()
    elif name == 'number_of_connections':
        # Get the number of currently connected sockets.
        return JsPyTextSocket.number_of_connections()
    elif name == 'set_connection_limit':
        # Set socket quantity limit.
        JsPyTextSocket.set_connection_limit(*args)
        return True
    elif name == 'clear':
        JsPyFunction.clear('py_normal')
        JsPyFunction.clear('py_exclusive')
        JsPyFunction.clear('py_sum')
        return True
    elif name == 'expose':
        JsPyFunction.expose('py_normal', py_normal)
        JsPyFunction.expose('py_exclusive', py_exclusive, True)
        JsPyFunction.expose('py_sum', positive_sum3)
        return True
    elif name == 'is_running':
        run1 = JsPyFunction.is_running('py_normal')
        run2 = JsPyFunction.is_running('py_exclusive')
        run3 = JsPyFunction.is_running('py_sum')
        return (f'py_normal: {run1}, py_exclusive: {run2}, '
                f'py_sum: {run3}')
    elif name == 'get_keys':
        all_names = JsPyFunction.get_keys()
        return all_names
    elif name == 'has':
        return JsPyFunction.has(*args)
    elif name == 'call_nowait':
        JsPyFunction.call_nowait(key)(*args)
        return True
    elif name == 'call':
        # timeout 25sec
        call_ack = await JsPyFunction.call(key, 25)(*args)
        return json.dumps(call_ack, cls=JsPyError.JSONEncoder)
    else:
        return False

def print_socket_event(id: int, event: str):
    """Print out socket open and close."""
    print(f'Socket {id}: {event}')
JsPyTextSocket.add_socket_event(print_socket_event)

@app.route('/call_nowait', ['GET'])
def page_call_nowait(request):
    if 'key' in request.query_params and\
       'args' in request.query_params:
        key = request.query_params['key']
        param = json.loads(request.query_params['args'])
        JsPyFunction.call_nowait(key)(*param)
        return PlainTextResponse('OK')

@app.route('/call', ['GET'])
async def page_call(request):
    if 'key' in request.query_params and\
       'args' in request.query_params:
        key = request.query_params['key']
        param = json.loads(request.query_params['args'])
        ret = await JsPyFunction.call(key)(*param)
        return PlainTextResponse(json.dumps(ret))
