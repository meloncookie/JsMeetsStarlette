import typing
import asyncio
import json
from JsMeetsStarlette import JsMeetsPy, JsPyQueue, JsPyFunction
from starlette.responses import PlainTextResponse

# Access http://xxx/static/index_queue.html
app = JsMeetsPy(debug=True, static='static',
                templates='templates')

def print_screen(key: str):
    """Callback function when queue data is received

    Parameters
    ----------
    key: str
        Key name which is an independent queue space
    """
    print('key: {} , data: {} has come.'.format(key, str(JsPyQueue.pop(key))))

# Register the callback function when the queue data arrives.
JsPyQueue.add_callback(print_screen)

# A method for a client to call an API on the server side.
@JsPyFunction.callable
async def push_nowait(key, value):
    await JsPyQueue.push_nowait(key)(value)
    return True

@JsPyFunction.callable
async def push(key, value):
    return await JsPyQueue.push(key, timeout=3)(value)

@JsPyFunction.callable
async def pop(key):
    return JsPyQueue.pop(key, '<<empty buffer>>')

@JsPyFunction.callable
async def shift(key):
    return JsPyQueue.shift(key, '<<empty buffer>>')

@JsPyFunction.callable
async def add_callback():
    JsPyQueue.add_callback(print_screen)
    return True

@JsPyFunction.callable
async def clear_callback():
    JsPyQueue.clear_callback()
    return True

@JsPyFunction.callable
async def is_empty(key):
    return JsPyQueue.is_empty(key)

@JsPyFunction.callable
async def has(key):
    return JsPyQueue.has(key)

@JsPyFunction.callable
async def get_keys():
    return JsPyQueue.get_keys()

@JsPyFunction.callable
async def clear(key):
    JsPyQueue.clear(key)
    return True

@JsPyFunction.callable
async def clear_all():
    JsPyQueue.clear_all()
    return True

@JsPyFunction.callable
async def remove(key):
    JsPyQueue.remove(key)
    return True

@JsPyFunction.callable
async def remove_all():
    JsPyQueue.remove_all()
    return True
