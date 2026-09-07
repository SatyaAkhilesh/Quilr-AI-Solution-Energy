
This repository contains four practical engineering tasks focused on MCP integration, AI gateway security, streaming guardrails, rate limiting, and resilient model routing.

The project is written in Python and uses:

- Python 3.12
- Official MCP Python SDK
- FastAPI
- Pydantic
- httpx
- aiosqlite
- pytest
- uvicorn

The main goal of the project is to demonstrate how I would build small gateway and integration components that sit between AI clients, MCP servers, and model providers.

---

# Project Structure

```text
fde-assessment/
│
├── task1_mcp_server/
│   ├── __init__.py
│   └── server.py
│
├── task2_mcp_gateway/
│   ├── __init__.py
│   ├── auth.py
│   ├── downstream_mock.py
│   └── gateway.py
│
├── task3_stream_guardrail/
│   ├── __init__.py
│   └── gateway.py
│
├── task4_model_router/
│   ├── __init__.py
│   ├── db.py
│   ├── mock_primary.py
│   ├── mock_backup.py
│   └── router.py
│
├── tests/
│   ├── __init__.py
│   ├── test_task1.py
│   ├── test_task2.py
│   ├── test_task3.py
│   └── test_task4.py
│
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md


**Workflow**

                     AI Client / Agent
                            |
                +-----------+-----------+
                |                       |
                v                       v
           MCP Gateway             LLM Gateway
                |                       |
                v                       v
           MCP Server            Guardrail / Router
                                        |
                             +----------+----------+
                             |                     |
                             v                     v
                       Primary Model          Backup Model

**Requirements**

Python 3.12+
Git
macOS / Linux / Windows
**
Create a virtual environment:

**
python3.12 -m venv .venv

**
Activate it on macOS/Linux:**

source .venv/bin/activate
