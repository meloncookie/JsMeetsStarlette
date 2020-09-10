/*
RingTypedArray.js

Overview
----------
Ring buffer library of fixed length arrays.
The buffer is a TypedArray(Uint8Array, Int8Array, etc...).

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
RingTypedArray
    constructor(arrayLength, ArrayType=Uint8Array, value=0)
        Create a fixed length ring buffer.
    fill(value=0)
        Fills the all elements with the specified value.
    isLittleEndian()
        Get the byte order of the browser.
    push(array)
        Push array in the ring array.
    shift()
        Get a copy of the ring array.(FIFO)
    pop()
        Get a copy of the ring array.(LIFO)

Examples
----------
// 5element, Uint16Array, initialize value 0.
let ring = new RingTypedArray(5, Uint16Array, 0);    // [0,0,0,0,0]
ring.push([1,2,3]);                                  // Array
ring.push(new Uint16Array([4,5]));                   // TypedArray
ring.push(new Uint16Array([6]).buffer);              // ArrayBuffer
ring.shift();                   // Uint16Array: [2,3,4,5,6]
ring.pop();                     // Uint16Array: [6,5,4,3,2]
ring.shift().buffer             // Arraybuffer: 10 bytes
Array.from(ring.shift());       // Array: [2,3,4,5,6]
*/
class RingTypedArray {
    /**
     * Create a fixed length ring buffer.
     * @param {number} arrayLength The length of array (not byteLength).
     * @param {TypedArray} [ArrayType=Uint8Array] Uint8Array, Int8Array, Uint16Array, ...
     * @param {number} [value=0] Ring array initialization value.
     */
    constructor(arrayLength, ArrayType=Uint8Array, value=0){
        this.VERSION = '0.0.0';
        this._unitLength = ArrayType.BYTES_PER_ELEMENT;
        if(arrayLength < 2){
            throw new Error("Invalid arrayLength in <RingBinaryArray>");
        }
        this._arrayLength = arrayLength;
        this._buffer = new ArrayType(arrayLength);
        this._ArrayType = ArrayType;
        this._buffer.fill(value);
        this._startIndex = 0;
        // Endian of browser. Little endian: true / Big endian: false
        this._endian = this._judgeEndian();
    }
    _judgeEndian(){
        let buffer = new ArrayBuffer(2);
        new DataView(buffer).setInt16(0, 256, true);
        return((new Int16Array(buffer)[0]) === 256);
    }
    /**
     * Get the byte order of the browser.
     * @returns {boolean} true: Little endian, false: Big endian
     */
    isLittleEndian(){
        return(this._endian);
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
     * Push array of argument to the ring array.
     *     When the parameter is ArrayBuffer instance,
     *     1. The byte length must be an integral multiple of the byte length of TypedArray.
     *     2. The byte order follows the native order of the PC on the browser side.
     *
     *     When the parameter is Array or TypedArray instance,
     *     1. Numerical values beyond the buffer's expressible range are rounded appropriately.
     * @param {Array|ArrayBuffer|TypedArray} arrayLike
     * @returns {boolean} true: success
     */
    push(arrayLike){
        let target = new (this._ArrayType)(arrayLike);
        let targetLength = target.length;

        if(targetLength >= this._arrayLength){
            this._buffer.set(target.subarray(targetLength-this._arrayLength));
            this._startIndex = 0;
        }
        else if(this._startIndex+targetLength > this._arrayLength){
            this._buffer.set(target.subarray(0, this._arrayLength-this._startIndex), this._startIndex);
            this._buffer.set(target.subarray(this._arrayLength-this._startIndex));
            this._startIndex = this._startIndex+targetLength-this._arrayLength;
        }
        else{
            this._buffer.set(target, this._startIndex);
            this._startIndex = this._startIndex+targetLength;
        }
        return(true);
    }
    /**
     * Get a copy of the ring array.
     * @returns {TypedArray} An array starting from the oldest element to the latest element.
     */
    shift(){
        let summary = new (this._ArrayType)(this._arrayLength);
        if(this._startIndex !== 0){
            summary.set(this._buffer.subarray(this._startIndex));
            summary.set(this._buffer.subarray(0, this._startIndex), this._arrayLength-this._startIndex);
        }
        else{
            summary.set(this._buffer);
        }
        return(summary);
    }
    /**
     * Get a copy of the ring array.
     * @returns {TypedArray} An array starting from the latest element to the oldest element.
     */
    pop(){
        let summary = new (this._ArrayType)(this._arrayLength);
        if(this._startIndex !== 0){
            summary.set(this._buffer.subarray(this._startIndex));
            summary.set(this._buffer.subarray(0, this._startIndex), this._arrayLength-this._startIndex);
        }
        else{
            summary.set(this._buffer);
        }
        return(summary.reverse());
    }
}