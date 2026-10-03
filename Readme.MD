# PAF FileFlow (FYP)

A PDF document processing and RAG chat application with a FastAPI backend and React frontend.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**
- **[Ollama](https://ollama.com/)** (local LLM — default model: `qwen3:4b-instruct`)
- **Tesseract OCR** (optional, for image text extraction in PDFs)
- API keys for external services you plan to use (see [Environment variables](#environment-variables))

## Setup

### 1. Clone and create a Python virtual environment

```bash
cd paf-fileflow
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root. At minimum, set the keys for the services you use:

| Variable | Description |
|---|---|
| `NOMIC_API_KEY` | Nomic Atlas API key (default embedding provider) |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_ENVIRONMENT` | Pinecone region (e.g. `us-east-1-aws`) |
| `PINECONE_INDEX_NAME` | Pinecone index name |
| `OLLAMA_BASE_URL` | Ollama server URL (default: `http://localhost:11434`) |
| `LLM_MODEL` | Ollama model name (default: `qwen3:4b-instruct`) |
| `SECRET_KEY` | JWT signing secret for auth |
| `PORT` | Backend port (default: `8001`) |
| `DATABASE_URL` | Database URL (default: `sqlite:///./chatbot.db`) |

Optional provider keys: `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `COHERE_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`.

### 4. Pull the Ollama model

```bash
ollama pull qwen3:4b-instruct
```

### 5. Install frontend dependencies

```bash
cd Frontend
npm install
cp .env.example .env
cd ..
```

The frontend `.env` should point at the backend:

```
VITE_API_URL=http://localhost:8001
```

## Running the project

You need **two terminals** — one for the backend and one for the frontend.

### Terminal 1 — Backend API

From the project root (with the virtual environment activated):

```bash
python run_api.py
```

The API starts at **http://localhost:8001**.  
Interactive docs: **http://localhost:8001/docs**

The SQLite database (`chatbot.db`) is created automatically on first startup.

### Terminal 2 — Frontend

From the project root:

```bash
python run_frontend.py
```

This launches the Vite dev server from the `Frontend` folder.  
Alternatively, run it manually:

```bash
cd Frontend
npm run dev
```

The dashboard opens at **http://localhost:5173**.

## Production build (frontend only)

```bash
cd Frontend
npm run build
npm run preview
```

## Database migrations

If you are upgrading an existing `chatbot.db`, run migrations from the project root:

```bash
python migration.py
```

## Troubleshooting

- **`npm not found`** — Install Node.js and ensure `npm` is on your PATH.
- **Ollama connection errors** — Make sure Ollama is running (`ollama serve`) and the model is pulled.
- **Frontend cannot reach the API** — Confirm the backend is running and `VITE_API_URL` in `Frontend/.env` matches the backend port.
- **OCR warnings** — Install Tesseract and add it to your PATH if you need image text extraction from PDFs.
