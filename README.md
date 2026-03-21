# black-core

BLACK ORIGIN Python-first autonomous runtime with:

- Runtime Engine + Event Bus
- Task Intelligence Engine
- Goal Generation Engine
- Agent System
- Executor Runner + Code Runner (real Python execution)
- Autonomous Loop
- FAISS semantic memory with sentence-transformers

## Runtime flow

`ANALYSIS → ARENA → EVALUATION → EVOLUTION → DESIGN → ACTION → MEMORY → LOOP`

## Setup

```bash
python -m pip install -r requirements.txt
python run.py
```

## Execution safety

- Executor blocks dangerous imports (`os`, `subprocess`, etc.) and dangerous calls (`os.system`, `exec`, `eval`).
- Generated code runs in a subprocess with timeout control and captured `stdout` / `stderr`.
