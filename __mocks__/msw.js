// Mock MSW
export const setupServer = jest.fn(() => ({
  listen: jest.fn(),
  close: jest.fn(),
  use: jest.fn(),
  resetHandlers: jest.fn(),
}))

export const http = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  head: jest.fn(),
  patch: jest.fn(),
}

export const HttpResponse = {
  json: jest.fn((data) => ({
    json: () => Promise.resolve(data),
    status: 200,
    headers: new Map(),
  })),
  text: jest.fn((text) => ({
    text: () => Promise.resolve(text),
    status: 200,
    headers: new Map(),
  })),
}

export default {
  setupServer,
  http,
  HttpResponse,
} 