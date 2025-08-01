// Environment configuration for the application
export const config = {
  // API base URL - defaults to localhost:8001 for development
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',

  // Health check interval in milliseconds
  healthCheckInterval: 30000,

  // SSE connection configuration
  sse: {
    // Retry configuration for SSE connections
    retryInterval: 1000,
    maxRetries: 3,
  },
} as const;

// API endpoints
export const endpoints = {
  health: `${config.apiBaseUrl}/health`,
  analyze: `${config.apiBaseUrl}/analyze`,
} as const;
