Yes — here is **Task 1 to Task 4 in one continuous README block**, cleaned up so you can copy it directly without the extra empty code fences.

````markdown
# Forward Deployed Engineer Assessment

This repository contains four practical engineering tasks focused on MCP integration, AI gateway security, streaming guardrails, rate limiting, and resilient model routing.

The project is written in Python and uses Python 3.12, the official MCP Python SDK, FastAPI, Pydantic, httpx, aiosqlite, pytest, and uvicorn.

The goal of this project is to build small, testable gateway and integration components that sit between AI clients, MCP servers, and model providers.

---

# Task 1 - Custom MCP Server

Task 1 exposes two MCP tools: `get_customer_record` and `trigger_refund`.

The server uses the official MCP Python SDK and stdio transport.

## get_customer_record

Input:

```json
{
  "customer_id": "CUST-12345"
}
````

The customer ID must match exactly:

```text
CUST-XXXXX
```

where `XXXXX` is five digits.

Valid examples:

```text
CUST-12345
CUST-67890
```

Invalid examples:

```text
12345
CUST-1234
CUST-123456
CUST-ABCDE
cust-12345
```

Example response:

```json
{
  "found": true,
  "customer_id": "CUST-12345",
  "record": {
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "status": "active"
  }
}
```

## trigger_refund

Input:

```json
{
  "customer_id": "CUST-12345",
  "amount": 25.5,
  "reason": "Customer requested a refund"
}
```

Validation rules:

```text
customer_id must match CUST-XXXXX
amount must be greater than 0
reason must contain at least 10 characters
```

Example response:

```json
{
  "success": true,
  "refund_id": "REF-12345",
  "customer_id": "CUST-12345",
  "amount": 25.5,
  "reason": "Customer requested a refund",
  "status": "submitted"
}
```

## Task 1 Workflow

```text
MCP Client
    |
    | tools/list
    v
MCP Server
    |
    | tool schemas
    v
Client
    |
    | tools/call
    v
Input Validation
    |
    +---- invalid ----> validation error
    |
    +---- valid
             |
             v
         Tool Logic
             |
             v
        MCP Response
```

## STDIO Handling

The server keeps MCP protocol traffic and logs separated.

```text
stdin  -> MCP requests
stdout -> MCP protocol output only
stderr -> logs and diagnostics
```

Logs are written to stderr so they do not interfere with the stdio protocol.

## Validation Behavior

Invalid tool arguments are rejected by the MCP SDK before the tool function runs.

This was verified in MCP Inspector using invalid values for `customer_id`, `amount`, and `reason`.

Example invalid input:

```json
{
  "customer_id": "BAD-ID",
  "amount": -5,
  "reason": "short"
}
```

The server logs rejected fields to stderr and does not expose a raw Python traceback to the client.

## Run Task 1

```bash
python task1_mcp_server/server.py
```

The process waits for MCP messages over stdio.

## Run with MCP Inspector

```bash
mcp dev task1_mcp_server/server.py
```

The Inspector should show:

```text
get_customer_record
trigger_refund
```

## Task 1 Tests

```bash
python -m pytest tests/test_task1.py -v
```

The tests cover valid and invalid customer IDs, positive and negative amounts, zero amount, valid refund reasons, and short refund reasons.

---

# Task 2 - MCP Security Gateway

Task 2 implements an HTTP JSON-RPC gateway between an AI client and a downstream MCP server.

The gateway reads the Bearer token, determines the role, inspects MCP requests, and blocks protected tools when necessary.

## Architecture

```text
AI Client
    |
    | Authorization: Bearer <token>
    v
MCP Gateway :8000
    |
    | inspect JSON-RPC method
    | inspect tool name
    | check user role
    v
Downstream MCP Server :8001
```

## Local Test Roles

```text
admin-token  -> admin
viewer-token -> viewer
```

The static mapping is only used for the assessment. In production, this would normally be replaced with JWT validation, OAuth/OIDC, or another identity provider.

## Authorization Rules

`tools/list` is forwarded normally.

For `tools/call`, the gateway checks `params.name`.

If the tool name starts with `admin_`, the caller must have the `admin` role.

Examples:

```text
viewer + get_customer_record -> allowed
admin + get_customer_record -> allowed
viewer + admin_reset_key -> blocked
admin + admin_reset_key -> allowed
```

Unauthorized admin tool calls return:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32001,
    "message": "Unauthorized Tool Call"
  }
}
```

The blocked request is returned directly by the gateway and is not sent to the downstream server.

## Task 2 Workflow

```text
Incoming Request
      |
      v
Read Bearer Token
      |
      v
Resolve Role
      |
      v
Read JSON-RPC Method
      |
      +----------------------+
      |                      |
      v                      v
 tools/list              tools/call
      |                      |
      |                 read params.name
      |                      |
      |                 starts admin_ ?
      |                   /        \
      |                 no          yes
      |                 |            |
      |                 |       role == admin?
      |                 |         /       \
      |                 |       yes        no
      |                 |        |          |
      +-----------------+--------+          |
                        |                   |
                        v                   v
                 Forward Request     Return -32001
                        |
                        v
                Downstream Server
```

## Start Downstream Server

```bash
cd /Users/akhil/FDE/fde-assessment
source .venv/bin/activate
uvicorn task2_mcp_gateway.downstream_mock:app --port 8001
```

## Start Gateway

```bash
cd /Users/akhil/FDE/fde-assessment
source .venv/bin/activate
uvicorn task2_mcp_gateway.gateway:app --port 8000
```

## Test tools/list

```bash
curl -s \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer viewer-token" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## Test Viewer Normal Tool

```bash
curl -s \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer viewer-token" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_customer_record",
      "arguments": {
        "customer_id": "CUST-12345"
      }
    }
  }'
```

## Test Viewer Admin Tool

```bash
curl -s \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer viewer-token" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "admin_reset_key",
      "arguments": {}
    }
  }'
```

Expected result:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32001,
    "message": "Unauthorized Tool Call"
  }
}
```

## Test Admin Tool

```bash
curl -s \
  -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-token" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "admin_reset_key",
      "arguments": {}
    }
  }'
```

## Task 2 Tests

```bash
python -m pytest tests/test_task2.py -v
```

The tests cover tool listing, normal viewer calls, blocked admin calls, valid admin calls, missing tokens, invalid JSON-RPC versions, invalid tool parameters, and blocked requests not being forwarded downstream.

---

# Task 3 - Streaming PII Guardrail

Task 3 implements an LLM streaming gateway that removes sensitive information while the response is still being streamed.

The guardrail currently detects:

```text
email addresses
SSNs
credit card numbers
```

Sensitive values are replaced with:

```text
[REDACTED]
```

## Example

Upstream response:

```text
Contact me at satya@example.com. My SSN is 123-45-6789. Card: 4111 1111 1111 1111.
```

Client receives:

```text
Contact me at [REDACTED]. My SSN is [REDACTED]. Card: [REDACTED].
```

## Cross-Chunk Handling

PII may be split across stream chunks.

Example:

```text
chunk 1: Contact me at satya@
chunk 2: example.com
```

A simple per-chunk regex check would miss this email.

The gateway keeps a bounded rolling buffer so sensitive values can still be detected when they cross chunk boundaries.

The same approach handles:

```text
chunk 1: 123-45-
chunk 2: 6789
```

and:

```text
chunk 1: 4111 1111
chunk 2: 1111 1111
```

## Streaming Workflow

```text
LLM Provider
     |
     | stream chunk
     v
Rolling Buffer
     |
     v
PII Detection
     |
     v
Redaction
     |
     v
Safe Stream to Client
```

The gateway keeps only a limited amount of recent text instead of storing the full response in memory.

This keeps memory bounded and preserves streaming behavior.

## Run Task 3

```bash
uvicorn task3_stream_guardrail.gateway:app --port 8002
```

## Test Task 3

```bash
curl -N \
  -X POST http://127.0.0.1:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Tell me something"
  }'
```

Expected output:

```text
Here is the response. Contact me at [REDACTED]. My SSN is [REDACTED]. Card: [REDACTED].
```

## Task 3 Tests

```bash
python -m pytest tests/test_task3.py -v
```

The tests cover email redaction, SSN redaction, credit card redaction, unchanged normal text, and sensitive values split across multiple chunks.

---

# Task 4 - Rate Limiter and Model Fallback Router

Task 4 implements a resilient LLM routing layer with token-aware rate limiting, SQLite persistence, timeout handling, and fallback between model providers.

The router supports:

```text
50,000 tokens per minute per tenant
on-disk SQLite usage tracking
primary model routing
automatic fallback on HTTP 429
automatic fallback after a 3000 ms timeout
sanitized gateway error responses
```

## Architecture

```text
Client
  |
  | X-API-Key
  v
Model Router :8100
  |
  v
Token Rate Limiter
  |
  +---- limit exceeded ----> HTTP 429
  |
  +---- allowed
           |
           v
      Primary Model :8101
           |
       +---+------------------+
       |                      |
    success               429 / timeout
       |                      |
       v                      v
    Client              Backup Model :8102
                               |
                               v
                             Client
```

## SQLite Storage

Token usage is stored in an on-disk SQLite database.

The table is created automatically:

```sql
CREATE TABLE IF NOT EXISTS token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_key TEXT NOT NULL,
    tokens INTEGER NOT NULL,
    created_at REAL NOT NULL
);
```

The database file is ignored by Git.

## Sliding Window Rate Limit

The limit is:

```text
50,000 tokens
per tenant
per 60 seconds
```

For each incoming request, the router calculates usage inside the current 60-second window.

Example:

```text
Current usage: 49,000
Incoming request: 2,000
Projected usage: 51,000
Limit: 50,000

Result: request rejected
```

Usage from different tenant API keys is tracked separately.

## Concurrency Handling

The rate-limit read, check, and insert operations are protected with an `asyncio.Lock`.

This prevents two concurrent requests in the same process from both reading the same token total and incorrectly passing the limit.

For a distributed production deployment, this would normally move to a shared atomic store such as Redis.

## Token Accounting

The router estimates request usage using both prompt size and requested output tokens.

```text
estimated usage =
estimated prompt tokens
+
max_tokens
```

The lightweight prompt estimate is suitable for the assessment.

A production gateway would normally use the exact tokenizer for the selected model.

## Start Primary Model

Terminal 1:

```bash
cd /Users/akhil/FDE/fde-assessment
source .venv/bin/activate
uvicorn task4_model_router.mock_primary:app --port 8101
```

## Start Backup Model

Terminal 2:

```bash
cd /Users/akhil/FDE/fde-assessment
source .venv/bin/activate
uvicorn task4_model_router.mock_backup:app --port 8102
```

## Start Router

Terminal 3:

```bash
cd /Users/akhil/FDE/fde-assessment
source .venv/bin/activate
uvicorn task4_model_router.router:app --port 8100
```

The client sends requests to the router on port `8100`.

## Test Normal Primary Routing

```bash
curl -s \
  -X POST http://127.0.0.1:8100/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-a" \
  -d '{
    "prompt": "hello",
    "max_tokens": 1000
  }'
```

Expected response:

```json
{
  "provider": "primary",
  "text": "Primary response for: hello"
}
```

## Test HTTP 429 Fallback

The primary mock returns HTTP 429 when the prompt is `rate-limit`.

```bash
curl -s \
  -X POST http://127.0.0.1:8100/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-b" \
  -d '{
    "prompt": "rate-limit",
    "max_tokens": 1000
  }'
```

Expected:

```json
{
  "provider": "backup",
  "text": "Backup response for: rate-limit"
}
```

Flow:

```text
Client
  |
  v
Router
  |
  v
Primary
  |
  | HTTP 429
  v
Backup
  |
  v
Client
```

## Test 3000 ms Timeout Fallback

The primary mock intentionally waits longer than 3 seconds when the prompt is `timeout`.

```bash
curl -s \
  -X POST http://127.0.0.1:8100/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-c" \
  -d '{
    "prompt": "timeout",
    "max_tokens": 1000
  }'
```

The router waits up to 3 seconds for the primary provider and then routes the request to the backup provider.

Expected:

```json
{
  "provider": "backup",
  "text": "Backup response for: timeout"
}
```

## Test Token Rate Limit

First send a request using a fresh tenant:

```bash
curl -s \
  -X POST http://127.0.0.1:8100/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-limit" \
  -d '{
    "prompt": "hello",
    "max_tokens": 49000
  }'
```

Then immediately send:

```bash
curl -s \
  -X POST http://127.0.0.1:8100/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-limit" \
  -d '{
    "prompt": "hello again",
    "max_tokens": 2000
  }'
```

The second request should exceed the limit and return a sanitized response similar to:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Token limit exceeded for this tenant",
    "request_id": "generated-request-id"
  }
}
```

## Error Sanitization

Raw upstream errors and Python stack traces are not returned to clients.

Instead, the router returns controlled errors such as:

```json
{
  "error": {
    "code": "UPSTREAM_UNAVAILABLE",
    "message": "Model service is temporarily unavailable",
    "request_id": "generated-request-id"
  }
}
```

The `request_id` can be used for troubleshooting without exposing internal implementation details.

## Task 4 Tests

```bash
python -m pytest tests/test_task4.py -v
```

The tests cover:

```text
usage below the limit
usage above the limit
tenant isolation
recent usage lookup
concurrent rate-limit requests
normal primary routing
429 fallback
timeout/failure behavior
```

---

# Run All Tests

Run the entire test suite before submission:

```bash
python -m pytest -v
```

All tests should pass.

---

# Security and Design Notes

The implementation intentionally keeps the services small and easy to test locally.

Security-related decisions include:

```text
MCP logs go to stderr instead of stdout
protected admin tools are denied before forwarding
JSON-RPC errors are controlled
SQL statements use parameters
SQLite usage is separated by tenant
upstream stack traces are not returned to clients
.env files are ignored
SQLite database files are ignored
virtual environments are ignored
```

---

# Production Improvements

The current implementation is designed for the assessment and local execution.

For production, I would replace the static Bearer token map with JWT or OAuth/OIDC validation.

I would replace the process-local `asyncio.Lock` and SQLite-backed distributed rate-limit coordination with a shared system such as Redis when running multiple gateway instances.

For PII detection, I would combine regex matching with stronger validation, including Luhn validation for payment card candidates and configurable organization-specific PII policies.

For model routing, I would add provider health checks, retry budgets, circuit breakers, structured metrics, distributed tracing, and provider-specific tokenizers.

For observability, I would track metrics such as:

```text
request latency
time to first token
rate-limit rejections
primary provider failures
fallback count
provider timeout count
PII redaction count
```

---

# Git Workflow

The project was developed incrementally using small Git checkpoints.

Example history:

```text
add rate limiting and model fallback
add streaming PII guardrail and tests
add MCP gateway auth and tests
add validation tests for task 1
add customer MCP tools and validation
add project dependencies
set up project structure
```

Before each commit:

```bash
python -m pytest -v
git status
git diff
```

Then:

```bash
git add .
git commit -m "short descriptive message"
git push
```
