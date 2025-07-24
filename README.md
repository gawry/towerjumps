# 🗼 Tower Jumps Analysis

A complete application for analyzing mobile carrier data to detect tower jumps, with a **CLI**, **FastAPI backend** and **React frontend**.


## 🚀 Quick Start (Docker Compose - Recommended)

Start both frontend and backend with one command:

```bash
# Start both services
docker compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8001
# Health Check: http://localhost:8001/health

# Stop services
docker compose down
```

That's it! The Docker setup includes live reloading for development.

## 🏗️ Architecture

```
towerjumps/
├── src/towerjumps/          # 🐍 FastAPI Backend (Port 8001)
├── frontend/                # ⚛️ React Frontend (Port 5173)
└── data/                    # 📊 Sample CSV files
└── tests/                   # AI Generated Test Cases
```

## 📊 Features

- **Real-time Analysis**: Upload CSV files and watch live progress via Server-Sent Events
- **Beautiful UI**: Modern React interface with drag & drop file upload
- **Configurable Parameters**: Time window, max speed, confidence threshold
- **Health Monitoring**: Automatic backend connectivity checks

## 🛠️ Manual Setup (Alternative)

If you prefer to run services separately:

### Backend
```bash
uv sync
uv run towerjumps-api
# Available at http://localhost:8001
```

### Frontend
```bash
cd frontend
pnpm install
echo "VITE_API_BASE_URL=http://localhost:8001" > .env.local
pnpm dev
# Available at http://localhost:5173
```

## 📡 Usage

1. Open http://localhost:5173
2. Upload a CSV file with carrier data
3. Configure analysis parameters
4. Start analysis and watch real-time results

## 🔧 Development Features (Docker Compose)

- **Live Reloading**: Changes to source code automatically reflected
- **Volume Mounting**: Source code mounted for real-time development
- **Network Communication**: Services communicate seamlessly

## 📁 CSV Data Format

Upload CSV files containing:
- Device/user identifiers
- Timestamp information
- Location data (coordinates, cell tower info)

Sample files are in the `data/` directory.

## 🛠️ Technologies

- **Backend**: FastAPI, Pandas, NumPy, SSE streaming
- **Frontend**: React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui
- **Real-time**: Server-Sent Events for live updates

## 📚 API Documentation

Visit http://localhost:8001/docs when the backend is running.


## 🖥️ Command Line Interface (CLI)

The CLI provides a powerful command-line interface for analyzing mobile carrier data to detect tower jumps.

### Installation & Setup

```bash
# Install dependencies
uv sync

# Verify installation
uv run towerjumps --help
```

### Basic Usage

```bash
# Analyze a CSV file with default settings
uv run towerjumps data/short.csv

# Specify custom output file
uv run towerjumps data/short.csv --output my_results.csv

# Run analysis with custom parameters
uv run towerjumps data/short.csv \
  --window 30 \
  --max-speed 65 \
  --confidence-threshold 0.7 \
  --output detailed_analysis.csv
```

### 📋 Command Options

| Option | Short | Default | Range | Description |
|--------|-------|---------|-------|-------------|
| `input_file` | - | *required* | - | Path to CSV file containing carrier data |
| `--output` | `-o` | `tower_jumps_analysis.csv` | - | Output CSV file path |
| `--window` | `-w` | `15` | 1-1440 | Time window size in minutes |
| `--max-speed` | `-s` | `80.0` | 1.0-200.0 | Maximum reasonable speed in mph |
| `--confidence-threshold` | `-c` | `0.5` | 0.0-1.0 | Minimum confidence threshold |
| `--quiet` | `-q` | `false` | - | Suppress verbose output |

### 📊 Examples

```bash
# Quick analysis with sample data
uv run towerjumps data/short.csv

# High-precision analysis (smaller windows, lower speed threshold)
uv run towerjumps data/short.csv \
  --window 10 \
  --max-speed 55 \
  --confidence-threshold 0.8

# Quiet mode for scripting
uv run towerjumps data/short.csv --quiet --output batch_results.csv

# Analyze large dataset with longer time windows
uv run towerjumps "data/20250709 4245337_CarrierData (new).csv" \
  --window 60 \
  --max-speed 75 \
  --output large_dataset_analysis.csv
```

### 🎨 CLI Features

- **📊 Real-time Progress**: Beautiful progress bars and status updates
- **🗺️ Data Summary**: Automatic validation and overview of input data
- **📈 Rich Output**: Color-coded results with tables and statistics
- **⚡ Fast Processing**: Efficient pandas-based analysis engine
- **📁 CSV Export**: Structured results ready for further analysis

### 📄 Output Format

The CLI generates a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| `start_time` | Beginning of time window |
| `end_time` | End of time window |
| `estimated_state` | Most likely location state |
| `is_tower_jump` | Boolean indicating tower jump detection |
| `confidence_percentage` | Confidence level (0-100%) |
| `record_count` | Number of records in window |
| `states_observed` | All states observed in window |
| `max_distance_km` | Maximum distance traveled |
| `max_speed_kmh` | Maximum speed observed |

### 🚀 Performance Tips

- **Small Windows** (5-15 min): Better precision, more detailed analysis
- **Large Windows** (30-60 min): Faster processing, broader patterns
- **High Speed Threshold**: More sensitive detection
- **Low Speed Threshold**: More conservative detection

### 📁 Sample Data

Use the provided sample files to test the CLI:

```bash
# Quick test with small dataset
uv run towerjumps data/short.csv

# Full analysis with larger dataset
uv run towerjumps "data/20250709 4245337_CarrierData (new).csv"
```
