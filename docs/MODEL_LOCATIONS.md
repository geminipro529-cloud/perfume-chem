# Model Locations

This repo has two startup paths, so there are two environment-file locations:

- Repo root `.env` or `.env.example`: used when you run `python run_api_server.py` from the repo root.
- `backend/.env` or `backend/.env.example`: used when you `cd backend` and run `poetry run uvicorn app.main:app --reload`.

## Where each model setting lives

### 1. Provider/model names in code

- Runtime defaults: [backend/app/core/config.py](/D:/chatbots/perfume-chem/backend/app/core/config.py)
- Registry and selector metadata: [backend/app/core/models_config.py](/D:/chatbots/perfume-chem/backend/app/core/models_config.py)
- Provider autodetection and service routing: [backend/app/services/ai/factory.py](/D:/chatbots/perfume-chem/backend/app/services/ai/factory.py)

These code files define model IDs such as:

- `OPENAI_MODEL`
- `CEREBRAS_MODEL`
- `HF_MODEL`
- `OLLAMA_MODEL`
- `LLAMA_CPP_MODEL_PATH`

## 2. Local filesystem locations

### Hugging Face local Transformers

- Env var: `HF_LOCAL_MODEL_PATH`
- Expected value: a directory containing a full Transformers model checkout
- Typical contents: `config.json`, tokenizer files, weight shards such as `model.safetensors`
- Example path:
  `models/llama3_8b_chat_uncensored`

Important: this repo does not currently contain a committed root `models/` directory. If you want to keep local Transformers models inside the repo tree, create `models/` yourself and point `HF_LOCAL_MODEL_PATH` at the model folder.

### llama.cpp local GGUF

- Env var: `LLAMA_CPP_MODEL_PATH`
- Expected value: one `.gguf` file
- Example path:
  `D:/models/OpenAi-GPT-oss-20b.gguf`

This is a file path, not a directory path.

### Ollama

- Env var: `OLLAMA_MODEL`
- Expected value: an Ollama model name such as `llama3.2:3b` or `hf.co/...`
- Actual model files are stored by Ollama, not by this repo
- Repo only needs the served model name plus `OLLAMA_BASE_URL`

### Remote API models

These do not live in the repo filesystem:

- `OPENAI_MODEL`
- `CEREBRAS_MODEL`
- `HF_MODEL` when using the Hugging Face Inference API
- `BASETEN_MODEL_ID`

They are provider-side identifiers, not local files.

## 3. Non-LLM model artifacts already in the repo

### Knowledge embeddings

- Source code: [engine/knowledge/embeddings.py](/D:/chatbots/perfume-chem/engine/knowledge/embeddings.py)
- Artifact directory: [data/embeddings](/D:/chatbots/perfume-chem/data/embeddings)
- Primary FAISS index: [data/embeddings/knowledge_index.faiss](/D:/chatbots/perfume-chem/data/embeddings/knowledge_index.faiss)
- Fallback numpy artifact: `data/embeddings/embeddings.npy` if FAISS is unavailable
- Metadata map: [data/embeddings/chunk_map.json](/D:/chatbots/perfume-chem/data/embeddings/chunk_map.json)

These are the repo’s semantic-search artifacts, not chat-model weights.

## 4. Recommended conventions

- If you run the API from repo root, copy `.env.example` to `.env` and edit it there.
- If you run the API from `backend/`, copy `backend/.env.example` to `backend/.env` and edit that file instead.
- Keep large local model weights outside git. Point env vars at them explicitly.
- Use `HF_LOCAL_MODEL_PATH` for a Transformers model directory.
- Use `LLAMA_CPP_MODEL_PATH` for a single GGUF file.
- Use `OLLAMA_MODEL` only for the served Ollama model name.
