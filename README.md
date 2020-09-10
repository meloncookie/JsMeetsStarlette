# JsMeetsStarlette

## Overview

There are many frameworks for creating web servers in python.
*Starlette* is a lightweight ASGI framework/toolkit,
which is ideal for building high performance asyncio services.

*JsMeetsStarlette* is a *Starlette* capsule library
that provides server functions and adds various functions.

1. You can call python functions from javascript in a natural way.
   The reverse is also true.
1. You can send arbitrary data from javascript to the queue
   on the python side. The reverse is also true.
1. Like MQTT, arbitrary data can be published/subscribed via the topic.

Real-time bidirectional communication becomes possible
without being aware of communication, you don't need
Ajax anymore.

---

## Version

0.0.0 : 2020.09.09

Major version 0 is under development. While making an example sample,
we will list the points to be improved and make improvements.

The official release is from major version 1.
We do software testing to improve quality.

---

## Requirements

* Python 3.7+
    * starlette > 0.13.2
* Javascript ES2017+

---

## Installation

```console
$ pip3 install starlette[full]
$ pip3 install JsMeetsStarlette
```
You'll also want to install an ASGI server, such as
[uvicorn](https://www.uvicorn.org/), daphne, or hypercorn.
```console
$ pip3 install uvicorn
```

See [GitHub](https://github.com/meloncookie/JsMeetsStarlette) for source and javascript code.

---

## Example 1/8 (Web server)

*JsMeetsStarlette.JsMeetsPy* is a *Starlette* capsule class.
Just replace the *Starlette* class and it becomes a web server.
The constructor arguments also conforms to the *Starlette* class.
Refer to [Starlette HP](https://www.starlette.io/)

- The websocket entry point opens in the background.
- Various functions are added through websocket.
- The user does not need to know the existence of websocket.

```python
# Only replace Starlette to JsMeetsPy. It's easy.
from JsMeetsStarlette import JsMeetsPy
from starlette.responses import JSONResponse

app = JsMeetsPy(debug=True)

@app.route('/', ['GET'])
async def homepage(request):
    return JSONResponse({'hello': 'world'})
```

---

## Example 2/8 (HTML)

Let's run javascript on the client browser.
Download the javascript code from
[GitHub](https://github.com/meloncookie/JsMeetsStarlette).

* Upload the HTML from the server.
* In the HTML, load the javascript file.
* Load `JsPyTextSocket.js` first, and the rest depending on the functions you use.
    * `JsPyFunction.js`
    * `JsPyQueue.js`
    * `JsPyPubsub.js`
* After loading `JsPyTextSocket.js`, background websocket will automatically connect.
* Stays connected for the life of this HTML page. You can link functions between client and server.

```bash
Project root directory
  ├─ main.py
  ├─ static
  │    └─ JsPyTextSocket.js, JsPyFunction.js, JsPyQueue.js, JsPyPubsub.js, etc...
  │    │  (It is included in the library, so copy it here.)
  │    └─ Other static files...
  ├─ templates
  │    └─ index.html
```

Create server on `main.py`

```python
from JsMeetsStarlette import JsMeetsPy

app = JsMeetsPy(debug=True, static='static', templates='templates')

@app.route('/', ['GET'])
async def homepage(request):
    return app.templates.TemplateResponse('index.html')
```

Create HTML on `index.html` (use Jinja2 template engine)

```HTML
<!DOCTYPE html>
<html>
    <head>
        <title>Title</title>
        <!-- Required basic library -->
        <script src="{{ url_for('static', path='/JsPyTextSocket.js') }}"></script>
        <!-- Extension library to load depending on the function used -->
        <script src="{{ url_for('static', path='/JsPyFunction.js') }}"></script>
        <script src="{{ url_for('static', path='/JsPyQueue.js') }}"></script>
        <script src="{{ url_for('static', path='/JsPyPubsub.js') }}"></script>
    </head>
    <body>
        ...
        <script>
            // Write javascript code.
        </script>
    </body>
</html>
```

> **app = JsMeetsPy(static='static', templates='templates')**
>
> Two special parameters can be added to *JsMeetsPy*
> inherited from *Starlette*.
>
> * **[static](https://www.starlette.io/staticfiles/)** :
> Directory name to be published statically.
> URL pathname /static/xxx allows direct access to file `xxx`
> in static directory.
> It is convenient for distributing images, icons, CSS, etc.
> [Click here for details.](https://www.starlette.io/staticfiles/)
>
> * **[templates](https://www.starlette.io/templates/)** :
> Directory name published by applying
> [Jinja2](https://palletsprojects.com/p/jinja/) template.
> Function *app.templates.TemplateResponse('filename')* can be used
> to respond with the templated HTML.
> [Click here for details.](https://www.starlette.io/templates/)

---

## Example3/8 (Call python function from javascript)

### **Python side**

The python side defines a **normal function** or **asynchronous function**.
Arguments and return values are arbitrary types
that can be converted to JSON format.

* int, float, str
* None (convert to null)
* True, False (convert to true, false)
* list (convert to Array)
* dict (convert to Object)
* tuple (convert to Array)

```python
from JsMeetsStarlette import JsMeetsPy, JsPyFunction

app = JsMeetsPy()

def add2(a, b):
    if a < 0 or b < 0:
        raise Exception('No negative arguments')
    return [a, b, a+b]
```

Next, expose the python function to javascript.
Use *JsPyFunction.expose()* method.

```python
# Bind key name 'py_add2' to function add2().
# Called by the client with this key name 'py_add2'.
JsPyFunction.expose('py_add2', add2)
```

### **Javascript side**

The following two scripts must be loaded beforehand.
* `JsPyTextSocket.js`
* `JsPyFunction.js`

If you expect a return value from python,
use *JsPyFunction.call()()* method.
Since it is handled as an **asynchronous function**,
the **await** keyword is required.

* *call()()* method is a double function call.
    * The first call specifies the key name and timeout [sec].
      Unlimited time if timeout is not specified.
    * The second call specifies any number of arguments.
      Keyword arguments are prohibited.
* When normal, the return value of python function is returned.
* When abnormal, an Error() exception is raised.
    * Communication error with the server.
    * When there is no response within the timeout period.
    * When an exception occurs in the called python function.

```javascript
async function call_python(){
    // Call python function by key name 'py_add2'
    ret1 = await JsPyFunction.call('py_add2')(4, 7);
    console.log(ret1);    // maybe [4,7,11]

    // With timeout
    try{
        ret2 = await JsPyFunction.call('py_add2', timeout=1)(-2, 5);
    }
    catch(e){
        console.log(e.message);
    }
}
```

Since it is an **asynchronous function**,
using the *then(), catch()* method without **await**
is also possible.

```javascript
// Process the return value without the await keyword.
JsPyFunction.call('py_add2')(4, 7).then(val => {
    console.log(val); });
```

If you do not expect the return value from python,
use *JsPyFunction.call_nowait()()* method.

* Do not wait for the return value and exception.
* Returns immediately.
* Only if it fails to send data to the server,
an *Error()* exception is raised.

```javascript
// Returns immediately.
JsPyFunction.call_nowait('py_add2')(4, 7);
```

---

## Example4/8 (Call javascript function from python)

### **Javascript side**

The following two scripts must be loaded beforehand.
* `JsPyTextSocket.js`
* `JsPyFunction.js`

The javascript side defines a **normal function** or
**asynchronous function**.
Arguments and return values are arbitrary types
that can be converted to JSON format.

* integer, number, string
* null, undefined, NaN, Infinity (convert to None)
* true, false (convert to True, False)
* Array (convert list)
* Object (convert dict)

```javascript
function sum_array(arr){
    let sum_all = 0;
    if(Math.random() < 0.1){
        throw Error('Random exception');
    }
    for(let item of arr){
        sum_all += item;
    }
    return(sum_all);
}
```

Next, expose the javascript function to python.
Use *JsPyFunction.expose()* method.

```javascript
// Bind key name 'sum_arr' to function sum_array().
// Called by the server with this key name 'sum_arr'.
JsPyFunction.expose("sum_arr", sum_array);
```

### **Python side**

If you expect a return value from javascript,
call it with the *JsPyFunction.call()()* method.
Since it is handled as an **asynchronous function**,
the **await** keyword is required.

* *call()()* method is a double function call.
    * The first call specifies the key name and timeout [sec].
      Unlimited time if timeout is not specified.
    * The second call specifies any number of arguments.
* An TypeError() exception is thrown, when the argument cannot
be converted to JSON format.

```python
from JsMeetsStarlette import JsMeetsPy, JsPyFunction

app = JsMeetsPy()

async def call_javascript():
    # Call python function by key name 'sum_arr'
    ret1 = await JsPyFunction.call('sum_arr', timeout=2)([1,2,3])
```

*JsPyFunction.call()()* calls all clients to which websocket is connected.
The return value is a dictionary type.

* **key**: soket ID that responded.
* **value**: the return value of the javascript function.


> **socket ID**
>
> When the client loads `JsPyTextSocket.js`,
> websocket is automatically connected with the server.
> A unique number is given to the connected websocket
> in the order of connection from 1.
>
> The number that identifies this client is called the socket ID.

> **value**
>
> When normal, value is the return value from javascript.
>
> In the following abnormal cases, value will be
> an exception instance.
>
> * JsPyError() instance, when communication error with clients.
> * JsPyError() instance, when an exception occurs in the called
>   javascript function.

When timeout is entered in the argument of *JsPyFunction.call()()*
method, only the response within the timeout period is valid.

If you do not specify timeout, wait until the return values from
all connected websockets are returned.

```python
async def call_javascript():
    ret1 = await JsPyFunction.call('sum_arr', timeout=2)([1,2,3])
# ex) ret1 = {1: 6, 4: 6, 9: JsPyError()}
# The socket ID1,4,9 clients responded within the time limit.
# Return values are 6 ( = 1+2+3 ).
#
# But an exception occurs in socket ID9 client.
```

If you do not expect the return value from javascript,
use *JsPyFunction.call_nowait()()* method.

* Do not wait for the return value and exception.
* Returns immediately.

```python
JsPyFunction.call_nowait('sum_arr')([4,7])
```

---

## Example5/8 (Send to python queue from javascript)

### **Javascript side**

The following two scripts must be loaded beforehand.
* `JsPyTextSocket.js`
* `JsPyQueue.js`

Send data to the queue on the python side.
The queue has an independent data space for each queue key name.

* Send the data with queue key name by *JsPyQueue.push_nowait()*.
* It is a double function call.
    * The first call specifies the queue key name string.
    * The second call specifies the data that can be converted
      to JSON format.

```javascript
// Send list data to queue key name 'q1'
// Raise Error() exception if there is an error in sending.
JsPyQueue.push_nowait('q1')([1,{'a': 1, 'b':10}]);
```

### **Python side**

Data is acquired by specifying the queue key name.
The acquired data is removed from the queue.

| JsPyQueue method | notes |
| --- | --- |
| is_empty('key name') | Whether there is data in the specified queue. |
| pop('key name') | Get latest data of the specified queue. None if empty. |
| shift('key name') | Get the oldest data of the specified queue. None if empty. |

```python
from JsMeetsStarlette import JsMeetsPy, JsPyQueue

app = JsMeetsPy()

def some_function():
    if not JsPyQueue.is_empty('q1'):
        print(JsPyQueue.pop('q1'))
```

---

## Example6/8 (Send to javascript queue from python)

### **Python side**

Send data to the queue on the javascript side.
Sent to all clients connected by websocket.

* Send the data with queue name by *JsPyQueue.push_nowait()*.
* It is a double function call.
    * The first call specifies the queue key name string.
    * The second call specifies the data that can be converted
      to JSON format.

```python
from JsMeetsStarlette import JsMeetsPy, JsPyQueue

app = JsMeetsPy()

def some_function():
    JsPyQueue.push_nowait('q1')('hello')
```

### **Javascript side**

The following two scripts must be loaded beforehand.
* `JsPyTextSocket.js`
* `JsPyQueue.js`

Data is acquired by specifying the queue key name.
The acquired data is removed from the queue.

| JsPyQueue method | notes |
| --- | --- |
| is_empty('key name') | Whether there is data in the specified queue. |
| pop('key name') | Get latest data of the specified queue. None if empty. |
| shift('key name') | Get the oldest data of the specified queue. None if empty. |

```javascript
if(! JsPyQueue.is_empty('q1')){
    var data = JsPyQueue.shift('q1');
}
```

---

## Example7/8 (Pub/Sub from javascript)

### **Javascript side**

The following two scripts must be loaded beforehand.
* `JsPyTextSocket.js`
* `JsPyPubsub.js`

You can send and receive data with the Pub/Sub model like MQTT.
The server acts as a broker.

1. A subscription is registered with a pair of topic name and
   callback function.
1. Each client registers the interested topic names with the server.
1. When a topic name and data pair is published,
   It will be sent to the server.(=broker)
1. The server resends it to the required clients.
1. When the published data arrives at the client,
   the corresponding callback function is called.
   Topic name and data are passed as arguments.


### **Javascript side Publish**

* Publish with *JsPyPubsub.publish()()* method.
* It is a double function call.
    * The first call specifies the topic name and timeout [sec].
      Unlimited time if not specified.
    * The second call specifies the data that can be converted
      to JSON format.

Since *publish()()* is **asynchronous function**,
add the **await** keyword.

* Returns true if the data was successfully sent to the server.
* Returns false if communication error or timeout occurs.
* If you don't need a return value, you can omit await keyword.
* Of course, besides the await keyword, you can also use the then() method.

```javascript
async function some_function(){
    // topic name: 'topic1', data: [null, 3]
    // If communication error or timeout occurs, false is returned.
    is_success = await JsPyPubsub.publish(
        'topic1', timeout=1)([null, 3]);
}
```

#### **Javascript side Subscribe**

A subscription is registered with a pair of topic name and
callback function. When the published data arrives at the client,
the corresponding callback function is called.

* Define a callback function with two arguments.
    * The first argument is the topic name string.
    * The second argument is the data.
* Register subscription with *JsPyPubSub.subscribe()* method.
    * The first argument is the topic name string.
    * The second argument is callback function called when the
      specified topic data is received.
    * The third argument is timeout [sec]. Unlimited time
      if timeout is not specified.

Since *subscribe()* is **asynchronous function**,
add the **await** keyword.

* Returns true if the registration of the subscription to the
  server is successful.
* Returns false if communication error or timeout occurs.
* If you don't need a return value, you can omit await keyword.
* Of course, besides the await keyword, you can also use the then() method.

```javascript
// Define a callback function with 2 parameters.
function cb_func(topic_name, data){
    ...
}
// Register subscription
async function some_function(){
    is_success = await JsPyPubsub.subscribe('topic1',
                                            cb_func,
                                            timeout=1);
}
```

### **Javascript side Unsubscribe**

Call *JsPyPubSub.unsubscribe()* to stop a registered subscription.
*unsubscribe()* method is also **asynchronous function**.
The handling is the same as *subscribe()* method.

```javascript
// Unregister subscription
async function some_function(){
    is_success = await JsPyPubsub.unsubscribe('topic1', timeout=1)
}
```

---

## Example8/8 (Pub/Sub from python)

### **Python side Publish**

* Publish with *JsPyPubsub.publish()()* method.
* It is a double function call.
    * The first call specifies the topic name.
    * The second call specifies the data that can be converted
      to JSON format.

*publish()()* is **normal function**, then no **await** keyword required.

```python
from JsMeetsStarlette import JsMeetsPy, JsPyPubsub

app = JsMeetsPy()

def some_function():
    JsPyPubsub.publish('topic2')({'a': [1, 2]})
```

### **Python side Subscribe**

* Define a callback function with two arguments.
    * The first argument is the topic name string.
    * The second argument is the data.
* Register subscription with *JsPyPubSub.subscribe()* method.
    * The first argument is the topic name string.
    * The second argument is callback function called when the
      specified topic data is received.

*subscribe()* is **normal function**, then no **await** keyword required.

```python
from JsMeetsStarlette import JsMeetsPy, JsPyPubsub

app = JsMeetsPy()

def cb_func(topic_name, data):
    ...

JsPyPubsub.subscribe('topic2', cb_func)
```

---

## Hint

### **Python side**

* This library does not support multi-process. Use main process.
* Use **asynchronous function** in the main thread.
* The python function registered as callback should not occupy
  a process for a long time.
    * Processing in a short time
    * **Asynchronous function** is recommended.
      Frequently, you should transfer control with *await asyncio.sleep(0)*.

### **Javascript side**

* The function will continue as long as the HTML page that loaded `JsPyTextSocket.js` is valid.
* The previous information is lost when the HTML page switches.
    * Exposed functions, queue data, subscribe registration, etc...
* Therefore, this library is suitable for SPA(Single Page Application).

### **etc**

* The python and javascript APIs have similar interfaces.
* Data that can be transmitted (arguments, return value) must be
  convertible to json format. For example, if numpy array,
  list it with the .tolist() method.
* WebSocket API for binary communication is also available. See `JsPyBinarySocket.py`.
* There are many other useful functions. See the python docstring.
* There may be a better interface for exchanging data between
  client and server. Please send me your new ideas.

### **Derived library**

The *FastAPI* framework also has a powerful library as useful as *Starlette*.
A corresponding library is also prepared separately.
It will be published under the name *JsMeetsFastAPI* soon.

The *Flask* framework is also a very popular framework.
There is no plan to support it.
Since it is a legacy framework, I recommend switching to a high-performance
*Starlette* or *FastAPI* framework with the same usability.

---

## License

This project is licensed under the terms of the MIT license.
