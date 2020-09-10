import typing
import asyncio
import json
from starlette.responses import PlainTextResponse
from JsMeetsStarlette import (JsMeetsPy, JsPyError, JsPyTextSocket,
                              JsPyPubsub, JsPyFunction)

# Access http://xxx/static/index_pubsub.html
app = JsMeetsPy(debug=True, static='static',
                templates='templates')

# When the topic name is "hello",
# a message will also be output to the server console.
@JsPyPubsub.subscribe('hello')
def topic_callback(topic, data):
    print(topic+": "+str(data))

# Test code ---------------------------------------
def new_topic_callback(topic, data):
    print(topic+">> "+str(data))

@JsPyFunction.callable
async def py_function(name:str, args:list):
    if name == 'subscribe':
        JsPyPubsub.subscribe('hello', new_topic_callback)
        return True
    elif name == 'unsubscribe':
        JsPyPubsub.unsubscribe('hello')
        return True
    elif name == 'publish':
        JsPyPubsub.publish(*args)({'name': 'server', 'message': 'hello'})
        return True
    elif name == 'get_topics':
        return JsPyPubsub.get_topics()
    else:
        return False
# -------------------------------------------------
