# PAF FileFlow (FYP)

A PDF document processing and RAG chat application with a FastAPI backend and React frontend.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**
- **OpenAI API key** (LLM: `gpt-4o`, Embeddings: `text-embedding-3-small`)
- **Pinecone account** (cloud vector database)
- **Tesseract OCR** (optional, for image text extraction in PDFs)

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
| `OPENAI_API_KEY` | **Required** — OpenAI API key (used for LLM and embeddings) |
| `PINECONE_API_KEY` | **Required** — Pinecone API key |
| `PINECONE_ENVIRONMENT` | Pinecone region (e.g. `us-east-1-aws`) |
| `PINECONE_INDEX_NAME` | Pinecone index name (must match your index's dimensions) |
| `VECTOR_DB_TYPE` | Vector DB backend — `pinecone` (default) or `local` |
| `LLM_MODEL` | OpenAI model name (default: `gpt-4o`) |
| `SECRET_KEY` | JWT signing secret for auth |
| `PORT` | Backend port (default: `8001`) |
| `DATABASE_URL` | Database URL (default: `sqlite:///./chatbot.db`) |

Optional provider keys for alternative embedding backends: `VOYAGE_API_KEY`, `COHERE_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`.

Example `.env`:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=researchmedical
VECTOR_DB_TYPE=pinecone
```

### 4. Install frontend dependencies

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

## LLM & Embedding Configuration

| Setting | Default | Notes |
|---|---|---|
| LLM Model | `gpt-4o` | Set via `LLM_MODEL` env var |
| LLM Temperature | `0.3` | Set via `LLM_TEMPERATURE` env var |
| LLM Max Tokens | `4000` | Set via `LLM_MAX_TOKENS` env var |
| Embedding Provider | `openai` | Set via `DEFAULT_EMBEDDING_PROVIDER` |
| Embedding Model | `text-embedding-3-small` | Set via `DEFAULT_EMBEDDING_MODEL` |
| Embedding Dimensions | `1024` | Must match your Pinecone index |

Alternative embedding providers supported: `voyageai`, `cohere`.

## Troubleshooting

- **`npm not found`** — Install Node.js and ensure `npm` is on your PATH.
- **OpenAI errors** — Verify your `OPENAI_API_KEY` is valid and has sufficient quota.
- **Pinecone connection errors** — Check `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, and `PINECONE_INDEX_NAME` are correctly set and the index exists with the right dimensions (1024).
- **Frontend cannot reach the API** — Confirm the backend is running and `VITE_API_URL` in `Frontend/.env` matches the backend port.
- **OCR warnings** — Install Tesseract and add it to your PATH if you need image text extraction from PDFs.
