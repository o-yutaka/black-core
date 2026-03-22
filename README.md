# black-core

BLACK ORIGIN Python-first autonomous runtime with:

- Runtime Engine + Event Bus
- Task Intelligence Engine
- Goal Generation Engine
- Agent System
- Executor Runner + Code Runner (real Python execution)
- X SNS Executor (real posting + metric pull)
- Performance Comparison Engine (simulation vs real)
- Autonomous Loop
- FAISS semantic memory with sentence-transformers

## Runtime flow

`ANALYSIS → ARENA → EVALUATION → EVOLUTION → DESIGN → ACTION → MEMORY → LOOP`

When `sns_request.platform == "x"`, the loop expands to:

`ANALYSIS → ARENA(X task build) → ACTION(X post + metrics) → PERFORMANCE COMPARISON → MEMORY → EVOLUTION`

## Setup

```bash
python -m pip install -r requirements.txt
python run.py
```

## X integration

Set real X credentials:

```bash
export X_API_KEY="..."
export X_API_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_TOKEN_SECRET="..."
export X_BEARER_TOKEN="..."
```

Then pass an SNS task through runtime state:

```python
{
  "goal": "Ship message and read real engagement",
  "sns_request": {
    "platform": "x",
    "operation": "post_and_fetch_metrics",
    "text": "BLACK ORIGIN executing in reality.",
    "simulation_metrics": {
      "likes": 50,
      "reposts": 10,
      "replies": 8,
      "quotes": 3,
      "impressions": 4000,
    },
  },
}
```

The system will post to X, fetch engagement metrics, compare simulation-vs-real outcomes, store both in memory, and bias next strategy from measured performance.

## Execution safety

- Executor blocks dangerous imports (`os`, `subprocess`, etc.) and dangerous calls (`os.system`, `exec`, `eval`).
- Generated code runs in a subprocess with timeout control and captured `stdout` / `stderr`.
