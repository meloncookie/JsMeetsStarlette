# Application example of JsMeetsStarlette

## Overview

This library is modularized for each function.
A sample case is introduced for each of the following
four functions.

1. **JsPyFunction** :
   You can call python functions from javascript in a natural way.
   The reverse is also true.
1. **JsPyQueue** :
   You can send arbitrary data from javascript to the queue
   on the python side. The reverse is also true.
1. **JsPyPubsub** :
   Like MQTT, arbitrary data can be published/subscribed via the topic.
1. **JsPyBinarySocket** :
   Binary communication between client and server.

---

## JsPyFunction

```console
$ uvicorn --port 8000 main_function:app
```

Launch your browser and open the following URL:
http://localhost:8000/static/index_function.html

---

## JsPyQueue

```console
$ uvicorn --port 8000 main_queue:app
```

Launch your browser and open the following URL:
http://localhost:8000/static/index_queue.html

---

## JsPyPubsub

```console
$ uvicorn --port 8000 main_pubsub:app
```

Launch your browser and open the following URL:
http://localhost:8000/static/index_pubsub.html

---

## JsPyBinarySocket

```console
$ uvicorn --port 8000 main_binary:app
```

Launch your browser and open the following URL:
http://localhost:8000/static/index_binary.html
