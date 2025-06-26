// Mock Supabase client
const mockSupabaseClient = {
  from: jest.fn(() => ({
    select: jest.fn(() => ({
      eq: jest.fn(() => ({
        data: [],
        error: null,
      })),
      data: [],
      error: null,
    })),
    insert: jest.fn(() => ({
      data: [],
      error: null,
    })),
    update: jest.fn(() => ({
      eq: jest.fn(() => ({
        data: [],
        error: null,
      })),
    })),
    delete: jest.fn(() => ({
      eq: jest.fn(() => ({
        data: [],
        error: null,
      })),
    })),
  })),
  auth: {
    getUser: jest.fn(() => Promise.resolve({ data: { user: null }, error: null })),
    signInWithOAuth: jest.fn(() => Promise.resolve({ data: null, error: null })),
    signOut: jest.fn(() => Promise.resolve({ error: null })),
    onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
  },
  channel: jest.fn(() => ({
    on: jest.fn().mockReturnThis(),
    subscribe: jest.fn().mockReturnThis(),
    unsubscribe: jest.fn(),
  })),
  removeChannel: jest.fn(),
}

export const createClient = jest.fn(() => mockSupabaseClient)

export default {
  createClient,
} 