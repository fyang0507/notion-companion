// Add global polyfills for Jest environment
require('whatwg-fetch')

// TextEncoder/TextDecoder polyfill for Node.js environment
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util')
  global.TextEncoder = TextEncoder
  global.TextDecoder = TextDecoder
}

// Stream API polyfills for MSW
if (typeof global.TransformStream === 'undefined') {
  const { TransformStream } = require('stream/web')
  global.TransformStream = TransformStream
}

if (typeof global.ReadableStream === 'undefined') {
  const { ReadableStream } = require('stream/web')
  global.ReadableStream = ReadableStream
}

if (typeof global.WritableStream === 'undefined') {
  const { WritableStream } = require('stream/web')
  global.WritableStream = WritableStream
}