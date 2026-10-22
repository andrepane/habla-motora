import test from 'node:test';import assert from 'node:assert/strict';
import {exactAudioBuffer} from '../frontend/recovered-audio.js';
test('recovered audio preserves exact visible bytes including a nonzero subarray offset',()=>{
 const buffer=Uint8Array.from([99,1,0,255,4,88]);const view=buffer.subarray(1,5),copy=exactAudioBuffer(view);
 assert.ok(copy instanceof ArrayBuffer);assert.deepEqual([...new Uint8Array(copy)],[1,0,255,4]);
 assert.equal(copy.byteLength,view.byteLength);assert.equal(exactAudioBuffer(copy),copy);
 new Uint8Array(copy)[0]=0;assert.equal(view[0],1);
});
