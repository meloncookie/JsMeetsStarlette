# coding: utf-8
import asyncio
import queue
import typing

__all__ = ['register_function']

"""Execute function call in background

Reserves the function for execution and later executes it
in the main thread's event loop.

Attributes
----------
register_function(func: typing.Callable, param) -> None
    Function call reservation
"""

# function call reservation
# Stack data is a tuple of two elements.
# The first element is a function, the second element is
# parameter of function.
_func_queue = queue.Queue()

_startup_task = None

def register_function(func: typing.Callable,
                      param: typing.Union[list, tuple, set]) -> None:
    """Function call reservation

    Outsource the function execution to the event loop of the main thread.
    The return value and exception of the function is ignored.

    Parameters
    ----------
    func: typing.Callable
        Normal function or async function.
    param: typing.Union[list, tuple, set]
        Function parameter, used as follows. func(*param)

    Examples
    ----------
    from JsMeetsStarlette import JsPyBackground

    def some_func(a, b, c):
        ...
        # The return value of the function is ignored.

    JsPyBackground.register_function(some_func, [1, 2, 3])
    """
    global _func_queue
    _func_queue.put_nowait((func, param))

async def startup_handler() -> None:
    """Start a background process in event loop thread"""
    global _startup_task
    _startup_task = asyncio.create_task(_event_loop())

async def shutdown_handler() -> None:
    """Shutdown processing when the server is shutdown"""
    global _startup_task
    if _startup_task:
        _startup_task.cancel()
        _startup_task = None

async def _event_loop() -> None:
    """Background process in event loop thread"""
    global _func_queue
    while True:
        if not _func_queue.empty():
            reserve = _func_queue.get_nowait()
            try:
                if asyncio.iscoroutinefunction(reserve[0]):
                    await reserve[0](*reserve[1])
                else:
                    reserve[0](*reserve[1])
            except asyncio.CancelledError:
                break
            except:
                pass
        await asyncio.sleep(0)
