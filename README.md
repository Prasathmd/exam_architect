# Exam-Architect AI

AI system that converts educational documents into bilingual MCQ questions (English and Tamil) for TNPSC, UPSC, SSC, and Banking exams.

## Architecture

- **Pipeline:** Upload → Extract → Chunk → Embed → Vector Store → RAG Retrieval → MCQ Generation → Validation → Export
- **Stack:** Python 3.12+, FastAPI, LangChain-style RAG, ChromaDB, PostgreSQL, Celery, Redis, Docker

## Quick start

### Local

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Set OPENAI_API_KEY or GOOGLE_API_KEY and DATABASE_URL, REDIS_URL
# Start PostgreSQL and Redis, then:
uvicorn main:app --reload
```

### Docker

```bash
export OPENAI_API_KEY=sk-...
docker compose up --build
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

## API examples

### 1. Upload document

```http
POST /api/upload
Content-Type: multipart/form-data
file: <binary textbook.pdf>
```

**Response:**

```json
{"job_id": "JOB1A2B3C4D", "status": "uploaded"}
```

### 2. Process document (chunk + embed)

```http
POST /api/process/{job_id}
```

**Response:**

```json
{"job_id": "JOB1A2B3C4D", "status": "ready"}
```

### 3. Generate MCQs (from text chunk)

```http
POST /api/generate
Content-Type: application/json

{
  "text_chunk": "Photosynthesis is the process by which plants convert light energy into chemical energy...",
  "num_questions": 5
}
```

**Response:** Plain exam-format text (no JSON):

```
1. Question in English
   (Tamil translation)

(A) Option English / Tamil
...
Answer: (C)
Explanation: ...
```

### 4. Generate MCQs from job (RAG)

```http
POST /api/questions/{job_id}/generate
```

Uses stored embeddings to retrieve relevant chunks and generate MCQs; stores result.

### 5. Get questions

```http
GET /api/questions/{job_id}
```

### 6. Export

```http
GET /api/export/{job_id}?format=docx
GET /api/export/{job_id}?format=pdf
```

Returns file download (DOCX or PDF when LibreOffice is available).

## Project structure

```
exam_architect/
  app/
    api/          # upload_api, question_api
    agents/       # upload, extraction, chunking, embedding, retrieval, mcq_generator, validation, export
    config/       # settings, llm_config
    db/           # session, models, repositories
    models/       # mcq_question, document_chunk, job_status
    services/     # document_parser, ai_client, vector_store, rag_pipeline
    tasks/        # Celery document_tasks
    utils/        # file_utils, text_utils
  main.py
  celery_app.py
  requirements.txt
  Dockerfile
  docker-compose.yml
```

## Environment

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async URL (e.g. `postgresql+asyncpg://user:pass@host:5432/db`) |
| `REDIS_URL` | Redis URL |
| `LLM_PROVIDER` | `openai` or `gemini` |
| `OPENAI_API_KEY` | Required if `LLM_PROVIDER=openai` |
| `GOOGLE_API_KEY` | Required if `LLM_PROVIDER=gemini` |

## Celery (optional)

Run a worker to offload processing:

```bash
celery -A celery_app worker --loglevel=info
```

Trigger from code: `process_document_task.delay(job_id, str(file_path))`.
