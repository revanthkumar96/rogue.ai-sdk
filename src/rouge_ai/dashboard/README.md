# Rouge.ai Dashboard

The Rouge.ai Dashboard provides a web-based UI for observing and interacting with your LLM applications. It displays real-time telemetry (traces, logs, metrics) and provides SDK documentation.

## Architecture

The dashboard consists of two parts:

1. **Frontend**: React 19 + Vite 6 application (located in `frontend_src/`)
2. **Backend**: FastAPI server that serves the static files and provides API endpoints (in `server.py`)

## Development

### Prerequisites

- Node.js 18+
- npm 9+

### Setup

```bash
cd src/rouge_ai/dashboard/frontend_src
npm install
```

### Development Mode

Run the frontend dev server with hot reload:

```bash
npm run dev
```

This starts Vite dev server at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

This compiles and bundles the React app into static files in `frontend_src/dist/`.

**Important**: After building, copy the files to the `static/` directory:

```bash
cp -r dist/* ../static/
```

The Python package includes files from `static/` (configured in `MANIFEST.in`).

## Deployment

The dashboard can be launched in two ways:

### 1. Standalone Mode (Separate Port)

```python
import rouge_ai

rouge_ai.init(service_name="my-app")
rouge_ai.launch_dashboard(port=10108)
```

Launches dashboard on `http://localhost:10108`

### 2. Mounted on FastAPI App (Recommended)

```python
import rouge_ai
from fastapi import FastAPI

app = FastAPI()
rouge_ai.init(service_name="my-app")
rouge_ai.connect_fastapi(app)  # Auto-mounts dashboard at /rouge
```

Dashboard available at `http://localhost:8000/rouge` (same port as your app)

## Troubleshooting

### Build Fails with "Package subpath './internal' is not defined"

This means Vite and @vitejs/plugin-react versions are incompatible.

**Solution**: Ensure you're using Vite 6.x with @vitejs/plugin-react 4.3.4:

```json
{
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
  }
}
```

Then run:
```bash
npm install
npm run build
```

### Build Fails with "Cannot resolve import 'react-is'"

The `recharts` library requires `react-is` as a peer dependency.

**Solution**: Add it to dependencies:

```json
{
  "dependencies": {
    "react-is": "^19.0.0"
  }
}
```

### Dashboard Shows Outdated UI

Make sure you copied the build files to `static/`:

```bash
cd frontend_src
npm run build
cp -r dist/* ../static/
```

## Dependencies

### Production Dependencies

- **react** 19.2.4 - UI framework
- **react-dom** 19.2.4 - React DOM renderer
- **react-is** 19.0.0 - React utilities (required by recharts)
- **framer-motion** 12.38.0 - Animation library
- **lucide-react** 0.577.0 - Icon library
- **recharts** 3.8.0 - Chart library for visualizations

### Development Dependencies

- **vite** 6.0.0 - Build tool and dev server
- **@vitejs/plugin-react** 4.3.4 - React plugin for Vite
- **eslint** 9.17.0 - Linter
- **TypeScript types** - Type definitions for React

## Project Structure

```
dashboard/
├── frontend_src/          # React source code
│   ├── src/
│   │   ├── App.jsx       # Main app component
│   │   ├── main.jsx      # Entry point
│   │   └── index.css     # Global styles
│   ├── package.json      # Dependencies
│   ├── vite.config.js    # Vite configuration
│   └── dist/             # Build output (gitignored)
├── static/               # Served by FastAPI (committed to git)
│   ├── index.html
│   └── assets/
│       ├── index-*.js
│       └── index-*.css
├── server.py             # FastAPI backend
└── README.md             # This file
```

## Build Pipeline

1. Edit React source in `frontend_src/src/`
2. Run `npm run build` to compile
3. Copy `dist/*` to `static/`
4. Commit changes to git
5. Python package includes `static/` via MANIFEST.in

## Future Enhancements

- WebSocket support for real-time updates (currently uses polling)
- Dark/light theme toggle
- Export traces/logs as JSON/CSV
- Interactive function replay
- SDK documentation tab with auto-generated API docs
