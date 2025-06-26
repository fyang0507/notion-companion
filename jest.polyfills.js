// Add global polyfills for Jest environment

// TextEncoder/TextDecoder polyfill for Node.js environment
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util')
  global.TextEncoder = TextEncoder
  global.TextDecoder = TextDecoder
}

// Fetch polyfill
if (typeof global.fetch === 'undefined') {
  global.fetch = require('node-fetch')
}