const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    // Mock Supabase modules
    '^@supabase/supabase-js$': '<rootDir>/__mocks__/supabase.js',
    '^msw/node$': '<rootDir>/__mocks__/msw.js',
    '^msw$': '<rootDir>/__mocks__/msw.js',
  },
  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/'],
  transformIgnorePatterns: [
    'node_modules/(?!(@supabase|msw)/)',
  ],
  collectCoverageFrom: [
    'components/**/*.{js,jsx,ts,tsx}',
    'hooks/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
  ],
  // Completely silent mode
  silent: true,
  verbose: false,
  maxWorkers: 1,
  forceExit: true,
  // Disable all output
  reporters: [
    ['default', { silent: true }]
  ],
  // Disable coverage reports to reduce noise
  collectCoverage: false,
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)