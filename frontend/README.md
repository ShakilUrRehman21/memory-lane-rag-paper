# 💻 Memory Lane RAG — Web Client

Interactive longitudinal research interface and knowledge explorer for **Memory Lane RAG**, built with React 18, TypeScript, and Vite.

---

## 🎨 Interface Capabilities

The frontend provides an intuitive, rich dark-mode workspace consisting of 8 dedicated exploratory views:

- 🧠 **Ask Memory Lane (`AskMemoryLaneView.tsx`)**: Natural language longitudinal query interface with real-time streaming, verified claim badges (`explicit`, `empirical_change`, `inferred_relationship`), citation sources, and epistemic uncertainty bounds.
- ⏳ **Chronological Timeline (`TimelineView.tsx`)**: Continuous zoomable chronological event stream with category filtering (`belief`, `goal`, `decision`, `preference`, `knowledge`, etc.) and visual stance polarity indicators.
- 📈 **Change Explorer (`ChangeExplorerView.tsx`)**: Visual trajectory analysis of detected semantic drift, transition velocities, and change-point turning intervals over multi-year horizons.
- ⚡ **Contradiction Inspector (`ContradictionView.tsx`)**: Deep inspection of stance polarity inversions, highlighting when and why earlier commitments were reversed or abandoned.
- 📄 **Version Diff (`VersionDiffView.tsx`)**: Side-by-side textual and structural comparison of document revisions (e.g., Resume 2019 vs. Resume 2026).
- 🕸️ **Temporal Memory Graph (`MemoryGraphView.tsx`)**: Interactive node-link relationship visualizer rendering directed transitions and connections between temporal memories.
- 📁 **Document Studio (`DocumentsView.tsx`)**: Drag-and-drop document ingestion studio supporting PDF, DOCX, TXT, and Markdown files with real-time Quad-Date and TMU extraction stats.
- 🔬 **Research Studio (`ResearchStudioView.tsx`)**: Empirical evaluation workbench executing real-time comparative benchmarks between Baseline RAG, Temporal RAG, and Memory Lane RAG.

---

## 🛠️ Tech Stack

- **Framework**: [React 18.3](https://react.dev) with [Vite 8](https://vitejs.dev)
- **Language**: [TypeScript 5.5](https://www.typescriptlang.org)
- **Styling**: Modern dark-mode design system with responsive layouts, CSS variables, and glassmorphism accents
- **API Client**: Strongly typed Fetch client ([`src/api.ts`](./src/api.ts)) with automatic error handling, active user session tokens, and proxying to the FastAPI backend

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: 18.0 or newer
- **Backend running**: Ensure the FastAPI server is running at `http://127.0.0.1:8000`

### 2. Install Dependencies
```bash
npm install
```

### 3. Development Server
```bash
npm run dev
```
Runs the app on `http://localhost:5173`. Requests to `/api/*` are automatically proxied to `http://127.0.0.1:8000` via Vite's dev server configuration.

### 4. Production Build
```bash
npm run build
```
Type-checks with `tsc -b` and bundles assets into the `dist/` directory.

---

## 🔗 Architecture Link
For comprehensive technical specifications, backend API details, and research benchmarks, refer to the [Root README.md](../README.md).
