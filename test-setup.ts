import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock global fetch
global.fetch = vi.fn()

// Mock performance.now for timing tests
global.performance = {
  ...global.performance,
  now: vi.fn(() => Date.now())
}

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}

// Mock Response class for better jsdom compatibility
global.Response = class MockResponse {
  status: number
  statusText: string
  headers: Map<string, string>
  body: any
  ok: boolean

  constructor(body: any, init: ResponseInit = {}) {
    this.status = init.status || 200
    this.statusText = init.statusText || 'OK'
    this.headers = new Map(Object.entries(init.headers || {}))
    this.body = body
    this.ok = this.status >= 200 && this.status < 300
  }

  async json() {
    if (typeof this.body === 'string') {
      return JSON.parse(this.body)
    }
    return this.body
  }

  async text() {
    return typeof this.body === 'string' ? this.body : JSON.stringify(this.body)
  }
}

// Mock ReadableStream for chat streaming tests
global.ReadableStream = class MockReadableStream {
  constructor(options?: any) {
    if (options?.start) {
      const controller = {
        enqueue: vi.fn(),
        close: vi.fn()
      }
      setTimeout(() => options.start(controller), 0)
    }
  }
}