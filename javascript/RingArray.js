/*
RingArray.js

Overview
----------
Ring buffer library of fixed length arrays.

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
RingArray
    constructor(arrayLength, value=0)
        Create a fixed length ring buffer.
    fill(value=0)
        Fills the all elements with the specified value.
    push(array)
        Push array in the ring array.
    shift()
        Get a copy of the ring array.(FIFO)
    pop()
        Get a copy of the ring array.(LIFO)

Examples
----------
let ring = new RingArray(5);    // [0,0,0,0,0]
ring.push([1,2]);
ring.push([3,4,5,6]);
ring.shift();                   // [2,3,4,5,6]
ring.pop();                     // [6,5,4,3,2]
ring.push([7])
ring.shift();                   // [3,4,5,6,7]
*/
class RingArray {
    /**
     * Create a fixed length ring buffer.
     * @param {number} arrayLength The length of ring array.
     * @param {any} [value=0] Ring array initialization value.
     */
    constructor(arrayLength, value=0){
        this.VERSION = '0.0.0';
        if(arrayLength < 2){
            throw new Error("Invalid byteLength in <RingArray>");
        }
        this._length = arrayLength;
        this._buffer = new Array(arrayLength);
        this._buffer.fill(value);
        this._startIndex = 0;
    }
    /**
     * Fills the all elements with the specified value.
     * @param {any} [value=0]
     */
    fill(value=0){
        this._buffer.fill(value);
        this._startIndex = 0;
    }
    /**
     * Push array in the ring array.
     * @param {any} array
     * @returns {boolean} true: success, false: failure
     */
    push(array){
        let firstLength;
        if(! Array.isArray(array)){
            return(false);
        }
        let array_length = array.length;
        if(array_length < 1){
            return(false);
        }
        else if(array_length >= this._length){
            this._buffer = array.slice(array_length-this._length);
            this._startIndex = 0;
        }
        else{
            if(this._startIndex+array_length > this._length){
                firstLength = this._length-this._startIndex;
                for(let i=0; i<firstLength; ++i){
                    this._buffer[this._startIndex++] = array[i];
                }
                this._startIndex = 0;
                for(let i=firstLength; i<array_length; ++i){
                    this._buffer[this._startIndex++] = array[i];
                }
            }
            else{
                for(let i=0; i<array_length; ++i){
                    this._buffer[this._startIndex++] = array[i];
                }
                if(this._startIndex == this._length){
                    this._startIndex = 0;
                }
            }
        }
        return(true);
    }
    /**
     * Get a copy of the ring array.(FIFO)
     * @returns {Array} An array starting from the oldest element to the latest element.
     */
    shift(){
        let summary = new Array(this._length);
        let index = 0;
        for(let i=this._startIndex; i< this._length; ++i){
            summary[index++] = this._buffer[i];
        }
        for(let i=0; i<this._startIndex; ++i){
            summary[index++] = this._buffer[i];
        }
        return(summary);
    }
    /**
     * Get a copy of the ring array.(LIFO)
     * @returns {Array} An array starting from the latest element to the oldest element.
     */
    pop(){
        let summary = new Array(this._length);
        let index = 0;
        for(let i=this._startIndex-1; i>=0; --i){
            summary[index++] = this._buffer[i];
        }
        for(let i=this._length-1; i>=this._startIndex; --i){
            summary[index++] = this._buffer[i];
        }
        return(summary);
    }
}