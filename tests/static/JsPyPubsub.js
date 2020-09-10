/*
JsPyPubsub.js

Overview
----------
A library that extends JsPyTextSocket.js. Load JsPyTextSocket.js before loading this library.
Any data can be exchanged using a PUB-SUB model such as MQTT.

License
----------
This software is released under the MIT License.
Copyright (c) 2020 meloncookie

Version
----------
0.0.0   2020.09.09

Requirements
----------
ES2017

Public functions
----------
JsPyPubsub
    subscribe(topic, func, timeout=0)
        Make a subscription reservation on the client side subscriber.
    unsubscribe(topic, timeout=0)
        Cancel a subscription reservation on the client side subscriber.
    publish(topic, suppress=false, timeout=0)(data)
        Publish the data associated with the topic name.
    get_topics()
        Get an array of all subscribed topic name.
*/
JsPyPubsub = {};
// constants ***************************
JsPyPubsub.VERSION = '0.0.0';
// valiable ****************************
JsPyPubsub._pubsub_id = 0;
JsPyPubsub._topic_callback = new Map();
JsPyPubsub._call_memory = new Map();
// function ****************************
/**
 * Make a subscription reservation on the client side subscriber.
 *     The subscription request notifies the server and is registered.
 *     Because it is a async function, you need the 'await' prefix to get the return value.
 * @param {string} topic Topic name to subscribe.
 * @param {Function} func Callbak function when the argument topic data is published.
 * @param {number} [timeout=0] Maximum time to wait for a response from the server.
 * @returns {boolean} true: Success, false: Failure
 */
JsPyPubsub.subscribe = async (topic, func, timeout=0) => {
    JsPyPubsub._pubsub_id += 1;
    if(JsPyPubsub._pubsub_id > JsPyTextSocket._MAX_ID){
        JsPyPubsub._pubsub_id = 1;
    }
    let this_id = JsPyPubsub._pubsub_id;
    let send_obj = {'protocol': 'sub_call', 'key': topic, 'id': this_id,
                    'data': null, 'exception': null};
    if(! JsPyTextSocket.send_json(send_obj)){
        return(false);
    }
    let call_promise = new Promise((resolve, reject) => {
        JsPyPubsub._call_memory.set(this_id, [resolve, reject]);
    });

    try{
        if(timeout === null || timeout <= 0){
            await call_promise;
        }
        else{
            await Promise.race([call_promise, JsPyTextSocket._time_raise(timeout)]);
        }
    }
    catch(error){
        return(false);
    }
    finally{
        JsPyPubsub._call_memory.delete(this_id);
    }
    JsPyPubsub._topic_callback.set(topic, func);
    return(true);
};
/**
 * Cancel a subscription reservation on the client side subscriber.
 *     The subscription request notifies the server and is registered.
 *     Because it is a async function, you need the 'await' prefix to get the return value.
 * @param {string} topic Topic name to subscribe.
 * @param {number} [timeout=0] Maximum time to wait for a response from the server.
 * @returns {boolean} true: Success, false: Failure
 */
JsPyPubsub.unsubscribe = async (topic, timeout=0) => {
    if(! JsPyPubsub._topic_callback.has(topic)){
        return(false);
    }
    JsPyPubsub._pubsub_id += 1;
    if(JsPyPubsub._pubsub_id > JsPyTextSocket._MAX_ID){
        JsPyPubsub._pubsub_id = 1;
    }
    let this_id = JsPyPubsub._pubsub_id;
    let send_obj = {'protocol': 'unsub_call', 'key': topic, 'id': this_id,
                    'data': null, 'exception': null};
    if(! JsPyTextSocket.send_json(send_obj)){
        return(false);
    }
    let call_promise = new Promise((resolve, reject) => {
        JsPyPubsub._call_memory.set(this_id, [resolve, reject]);
    });

    try{
        if(timeout === null || timeout <= 0){
            await call_promise;
        }
        else{
            await Promise.race([call_promise, JsPyTextSocket._time_raise(timeout)]);
        }
    }
    catch(error){
        return(false);
    }
    finally{
        JsPyPubsub._call_memory.delete(this_id);
    }
    JsPyPubsub._topic_callback.delete(topic);
    return(true);
};
/**
 * Publish the data associated with the topic name.
 *     The published data is once sent to the server.
 * @param {string} topic Topic name to publish.
 * @param {boolean} [suppress=false] If true, suppress the distribution of data from broker to myself.
 * @param {number} [timeout=0] Maximum time to wait for a response from the server.
 * @returns {async function} Async function that gives a data as an argument.
 *    The published data that can be converted to JSON format. Returns true if success.
 */
JsPyPubsub.publish = (topic, suppress=false, timeout=0) => {
    async function inner(data){
        JsPyPubsub._pubsub_id += 1;
        if(JsPyPubsub._pubsub_id > JsPyTextSocket._MAX_ID){
            JsPyPubsub._pubsub_id = 1;
        }
        let this_id = JsPyPubsub._pubsub_id;
        let send_obj = {'protocol': 'pub_call', 'key': topic, 'id': this_id,
                        'data': data, 'exception': suppress};
        if(! JsPyTextSocket.send_json(send_obj)){
            return(false);
        }
        let call_promise = new Promise((resolve, reject) => {
            JsPyPubsub._call_memory.set(this_id, [resolve, reject]);
        });

        try{
            if(timeout === null || timeout <= 0){
                await call_promise;
            }
            else{
                await Promise.race([call_promise, JsPyTextSocket._time_raise(timeout)]);
            }
        }
        catch(error){
            return(false);
        }
        finally{
            JsPyPubsub._call_memory.delete(this_id);
        }
        return(true);
    }
    return(inner);
};
/**
 * Get an array of all subscribed topic name.
 * @returns {Array} Array of Subscribed topic name.
 */
JsPyPubsub.get_topics = () => {
    return(Array.from(JsPyPubsub._topic_callback.keys()));
};
/**
 * Processes data with protocol 'pub_return', 'sub_return', 'unsub_return'
 */
JsPyPubsub._return_call = (obj_data) => {
    let id = obj_data['id'];
    let success = (obj_data['exception'] === null);
    if(JsPyPubsub._call_memory.has(id)){
        if(success){
            // resolve(true);
            JsPyPubsub._call_memory.get(id)[0](true);
        }
        else{
            // reject("error message...")
            JsPyPubsub._call_memory.get(id)[1](obj_data['exception']);
        }
    }
};
/**
 * Processes data with protocol 'pub'
 */
JsPyPubsub._pub = (obj_data) => {
    let topic = obj_data['key'];
    let data = obj_data['data'];
    try{
        if(JsPyPubsub._topic_callback.has(topic)){
            JsPyPubsub._topic_callback.get(topic)(topic, data);
        }
    }
    catch(e){
        // Do nothing
    }
};

JsPyTextSocket._add_protocol('pub_return', JsPyPubsub._return_call);
JsPyTextSocket._add_protocol('sub_return', JsPyPubsub._return_call);
JsPyTextSocket._add_protocol('unsub_return', JsPyPubsub._return_call);
JsPyTextSocket._add_protocol('pub', JsPyPubsub._pub);
