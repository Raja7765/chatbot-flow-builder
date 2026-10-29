# Chatbot Flow Builder - Frontend

Interactive React Flow application built with **React**, **Vite**, and **`@xyflow/react`**.

## Prerequisites

- [Node.js](https://nodejs.org/) (version 18 or higher recommended)
- npm (comes bundled with Node.js)

Verify Node.js is installed by running:
```powershell
node -v
npm -v
```
*(If Node.js is not yet installed on Windows, download the LTS installer from [nodejs.org](https://nodejs.org/) or install via winget: `winget install OpenJS.NodeJS.LTS`)*

---

## Getting Started

### 1. Navigate to the `frontend/` directory
From the project root:
```powershell
cd frontend
```

### 2. Install dependencies
```powershell
npm install
```
This will install `react`, `react-dom`, `@xyflow/react`, `vite`, and `@vitejs/plugin-react`.

### 3. Start the development server
```powershell
npm run dev
```

The application will start on `http://localhost:5173`. Open this URL in your web browser.

---

## Features

- **Interactive Canvas**: Drag, pan, zoom, connect, and delete nodes. Powered by `@xyflow/react`.
- **Pre-configured Nodes**:
  - **Start Node**: Flow entry point.
  - **Message Node**: Automated chatbot response.
- **Node Sidebar**: Drag-and-drop or click to place new nodes onto the canvas.
- **Properties Panel**: Select any node on the canvas to edit its label and message text in real time.
- **Schema Compatibility**: Automatically formats flow configurations to match the FastAPI backend `POST /flows` and `PUT /flows/{flow_id}` schema:
  - `nodes`: `[{ id, type, data: { label, text }, position: { x, y } }]`
  - `edges`: `[{ id, source, target }]`
- **View JSON / Save Flow**: Inspect and copy the formatted JSON payload ready for API submission.

---

## Scripts

- `npm run dev`: Launch the local development server with Hot Module Replacement (HMR).
- `npm run build`: Compile and bundle production-ready static assets into `dist/`.
- `npm run preview`: Locally preview the production build.
