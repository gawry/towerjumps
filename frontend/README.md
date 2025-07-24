# 🗼 Tower Jumps Analysis - Frontend

A React application built with Vite and shadcn/ui for analyzing mobile carrier data to detect tower jumps with real-time streaming.

## Features

- **File Upload**: Drag & drop or browse CSV files containing carrier data with validation
- **Real-time Analysis**: Server-Sent Events (SSE) streaming using modern [`eventsource-client`](https://www.npmjs.com/package/eventsource-client)
- **Configuration**: React Hook Form with Zod validation for robust form handling
- **Health Monitoring**: Backend API health check with automatic retries
- **Beautiful UI**: Modern interface built with shadcn/ui components and Tailwind CSS
- **Environment Configuration**: Configurable API endpoints via environment variables

## Prerequisites

- Node.js 18+ (with pnpm package manager)
- Backend API running (configurable via environment variables)

## Installation

```bash
# Install dependencies
pnpm install

# Set up environment variables (create .env.local)
echo "VITE_API_BASE_URL=http://localhost:8001" > .env.local

# Start development server
pnpm dev
```

The application will be available at `http://localhost:5173` (or the next available port).

## Environment Variables

Create a `.env.local` file in the frontend directory:

```bash
# Backend API base URL
VITE_API_BASE_URL=http://localhost:8001

# Optional: For production deployment
# VITE_API_BASE_URL=https://your-api-domain.com
```

## Architecture

The application follows a modern React architecture with custom hooks:

```
app/
├── components/
│   ├── ui/                 # shadcn/ui components
│   ├── TowerJumpsAnalyzer  # Main app component
│   ├── UploadForm          # File upload with React Hook Form + Zod
│   ├── AnalysisResults     # Real-time results display
│   └── HealthCheck         # API status monitor
├── hooks/
│   └── useAnalysis.ts      # Custom hook for SSE analysis
├── lib/
│   ├── config.ts           # Environment configuration
│   └── utils.ts            # Utility functions
└── routes/
    └── home.tsx            # Main route
```

## Usage

1. **Backend Setup**: Ensure the Tower Jumps Analysis API is running on the configured port
2. **Upload Data**: Drag and drop a CSV file or click to browse
3. **Configure Analysis**: Adjust parameters with real-time validation:
   - **Time Window**: Analysis window in minutes (1-1440)
   - **Max Speed**: Maximum reasonable travel speed in mph (0-200)
   - **Confidence Threshold**: Minimum confidence for detection (0.0-1.0)
4. **Start Analysis**: Click "Start Analysis" to begin processing
5. **View Results**: Monitor real-time progress and detected tower jumps

## CSV File Format

The CSV file should contain carrier data with location and timestamp information. The exact column names will depend on your backend implementation, but typically includes:

- Device ID or identifier
- Timestamp/datetime
- Location information (coordinates, cell tower info, etc.)

**File Requirements:**
- Must be CSV format (`.csv` extension)
- Maximum size: 50MB
- Contains proper headers and data structure

## API Integration

The frontend communicates with the backend API via:

- **Health Check**: `GET /health` - Monitors backend status (every 30 seconds)
- **Analysis**: `POST /analyze` - Uploads file and receives SSE stream

### SSE Events

The analysis endpoint streams various event types:

- `analysis_start` - Analysis has begun
- `progress` - Progress updates with percentage
- `processing_batch` - Batch processing information
- `tower_jump_detected` - Tower jump found with details
- `analysis_complete` - Analysis finished with summary
- `error` - Error occurred during processing

## Key Technologies

### Core Stack
- **React 19**: Modern React with hooks
- **Vite**: Fast development and build tool
- **TypeScript**: Type safety and better developer experience
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: Beautiful, accessible UI components
- **React Router v7**: Modern routing solution

### Form & Validation
- **React Hook Form**: Performant forms with minimal re-renders
- **Zod**: TypeScript-first schema validation
- **shadcn/ui Form**: Integrated form components

### Real-time Communication
- **[eventsource-client](https://www.npmjs.com/package/eventsource-client)**: Modern SSE client with POST support
- **Custom useAnalysis Hook**: Encapsulated SSE logic with proper cleanup

## Development

```bash
# Start development server with hot reload
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Type checking
pnpm typecheck
```

## Error Handling

- **Form validation** with real-time feedback and Zod schemas
- **File validation** (type, size) with visual error states
- **Network errors** displayed to users with retry options
- **SSE connection errors** with automatic cleanup
- **Health check failures** with manual retry capability

## Performance Features

- **Modern SSE client** with proper connection management
- **React Hook Form** for minimal re-renders
- **Custom hooks** for reusable stateful logic
- **Efficient state management** with proper cleanup
- **Real-time updates** without polling overhead
- **Progress indicators** for user feedback

## Production Deployment

### Environment Setup
```bash
# Production environment variables
VITE_API_BASE_URL=https://your-production-api.com
```

### Build & Deploy
```bash
# Build for production
pnpm build

# The build/ directory contains static files ready for deployment
# Deploy to any static hosting service (Vercel, Netlify, etc.)
```

## Contributing

When contributing:
1. Maintain TypeScript strict mode
2. Use React Hook Form for new forms
3. Validate with Zod schemas
4. Follow shadcn/ui patterns
5. Test SSE connections thoroughly
