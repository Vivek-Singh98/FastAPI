
# FastAPI Interview Notes

Use this guide to explain concepts aloud, then demonstrate them with [main.py](main.py). Examples use Pydantic v2. This covers the main interview areas, rather than every framework feature.

## 1. What is FastAPI?

FastAPI is a Python framework for building APIs with type-driven request parsing, validation, serialization, and generated OpenAPI documentation. Starlette provides web/ASGI capabilities; Pydantic handles data models. Uvicorn is an ASGI server that runs the application.

**Interview answer:** “I define typed endpoint functions and models. FastAPI uses them to validate incoming requests and generate an API contract. I still design the business rules, storage, and authorization.”

ASGI supports asynchronous request handling and protocols such as WebSockets. WSGI is the older synchronous application-server interface. An ASGI framework does not automatically make blocking libraries asynchronous. [FastAPI introduction](https://fastapi.tiangolo.com/)

## 2. Routing and request parameters

```python
from typing import Annotated
from fastapi import FastAPI, Header, Path, Query

app = FastAPI()

@app.get("/items/{item_id}")
def read_item(
    item_id: Annotated[int, Path(gt=0)],
    q: Annotated[str | None, Query(max_length=50)] = None,
    user_agent: Annotated[str | None, Header()] = None,
):
    return {"item_id": item_id, "q": q, "user_agent": user_agent}
```

| Input | Example | Declaration |
| --- | --- | --- |
| Path | `/items/7` | Parameter matching `{item_id}` |
| Query | `?q=python` | Scalar parameter / `Query` |
| JSON body | `{"title":"Study"}` | Pydantic model / `Body` |
| Header | `User-Agent: ...` | `Header` |
| Cookie | Session cookie | `Cookie` |
| Form | Form submission | `Form` |
| File | Multipart upload | `UploadFile` / `File` |

Declare fixed paths such as `/users/me` before overlapping dynamic paths such as `/users/{user_id}`. Form and file parsing require `python-multipart`. `UploadFile` uses a spooled file; accepting `bytes` reads the entire upload into memory. Standard JSON bodies and multipart uploads have different encodings. [Request parameter guide](https://fastapi.tiangolo.com/tutorial/path-params/), [file uploads](https://fastapi.tiangolo.com/tutorial/request-files/)

## 3. Pydantic and validation

`BaseModel` defines a schema. `Field` adds constraints; `field_validator` handles custom field rules and `model_validator` handles relationships between fields. Type hints alone do not enforce runtime types in ordinary Python; Pydantic performs that validation here.

- `model_dump()` produces a Python dictionary; `model_dump(mode="json")` makes values JSON-compatible.
- `model_dump_json()` produces a JSON string.
- `model_validate(data)` validates input and returns a model.
- `model_copy(update=...)` does **not** validate the update data.
- Use `ConfigDict(extra="forbid")` to reject unknown input fields.
- Validation may coerce compatible values. Use strict types/settings if coercion is unsuitable.
- Prefer separate create, update, and read models so clients cannot set server-controlled fields.

**Required vs nullable:** `name: str | None` is required but may be null. `name: str | None = None` may be omitted and may be null. `name: str` is required and cannot be null. [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [Pydantic fields](https://docs.pydantic.dev/latest/concepts/fields/)

In this repository, PATCH allows omission of all fields but explicitly rejects null for `title` and `completed`. Null is allowed for `content` to clear it.

## 4. HTTP methods and idempotency

| Method | Intended operation | Safe? | Idempotent? |
| --- | --- | --- | --- |
| GET | Retrieve | Yes | Yes |
| POST | Create / submit processing | No | Not generally |
| PUT | Replace target resource | No | Yes |
| PATCH | Apply partial changes | No | Depends on operation |
| DELETE | Remove target resource | No | Yes |

Safe means the client is not asking to change server state. Idempotent means repeating the request has the same intended effect on resource state; status codes need not match. A second DELETE may return 404 after the first returns 204. Setting a field to a fixed value can be an idempotent PATCH; incrementing a counter generally is not.

For a POST that must tolerate retries, design an idempotency-key mechanism. Use plural resource names such as `/notes` and HTTP verbs for operations. [HTTP method semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-method-definitions), [PATCH specification](https://www.rfc-editor.org/rfc/rfc5789.html)

## 5. PUT vs PATCH: the common interview trap

PUT replaces the writable representation. This demo requires a title and resets omitted content/completed to their defaults. PATCH retains omitted fields.

```python
changes = payload.model_dump(exclude_unset=True)
merged = {**existing.model_dump(), **changes}
updated = NoteRead.model_validate(merged)
```

Do not use `exclude_none=True` when null means “clear this value”; it would drop that instruction. Do not use truthiness checks such as `if payload.completed` because valid values include `False`, `0`, and empty strings. Define empty PATCH behavior explicitly. This demo treats `{}` as a no-op. [FastAPI body updates](https://fastapi.tiangolo.com/tutorial/body-updates/)

## 6. Response models and status codes

`response_model` documents, validates, serializes, and filters output. A public model can omit internal fields such as password hashes. Returning a raw `Response` bypasses normal model processing, so construct it deliberately. Invalid response data indicates a server bug; invalid request data normally generates a 422 response. [Response models](https://fastapi.tiangolo.com/tutorial/response-model/)

| Code | Typical meaning |
| --- | --- |
| 200 | Successful read or update |
| 201 | Resource created |
| 202 | Accepted for processing, not necessarily completed |
| 204 | Successful response without a body |
| 400 | Bad request / application-specific malformed input |
| 401 | Missing or invalid authentication; appropriate challenge header |
| 403 | Access forbidden |
| 404 | Resource not found |
| 409 | Conflict, such as duplicate unique value |
| 422 | FastAPI's normal request validation failure |
| 429 | Too many requests |
| 500 | Unexpected server failure |

Raise `HTTPException`, rather than returning it. Use exception handlers for consistent application error formats. Avoid catching every exception and returning 200. [Error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)

## 7. `def`, `async def`, and performance

Use `async def` when calling awaitable I/O clients and use `await` for their operations. Normal `def` endpoints and dependencies run in a thread pool. A normal helper called directly inside an async endpoint is **not** automatically moved to that pool.

```python
# Good with an async HTTP client:
async def fetch_remote(client):
    response = await client.get("https://example.com")
    return response.status_code
```

Do not call blocking `requests.get()` or `time.sleep()` directly on the event loop. Use an async alternative or explicitly offload blocking work. Async improves concurrency while waiting for I/O; it does not accelerate CPU-heavy work. CPU-heavy jobs may need processes or external workers. Bound concurrency, use timeouts, and measure bottlenecks. [Concurrency guide](https://fastapi.tiangolo.com/async/)

## 8. Dependency injection

`Depends` declares reusable prerequisites such as a database session, current user, or query settings. FastAPI resolves dependencies, supports nested dependencies, and normally caches the same dependency within a request. `use_cache=False` changes that behavior. Dependencies can be sync or async.

```python
def get_settings():
    return {"page_size": 10}

@app.get("/settings-demo")
def settings_demo(settings=Depends(get_settings)):
    return settings
```

A dependency using `yield` can acquire a resource and clean up in `finally`; for example, open and close a database session. Understand the configured dependency scope when resources interact with streaming responses. In tests, replace dependencies through `app.dependency_overrides`. [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/), [sub-dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/), [yield dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)

## 9. Databases, transactions, and migrations

A Pydantic model validates application data; an ORM model maps persistent database data. SQLAlchemy and SQLModel are common choices. Use a request-scoped session and a connection pool, rather than sharing one session across requests.

For a write, validate input, enforce authorization, modify within a transaction, commit, and handle rollback on failure. `flush` sends pending SQL without committing the transaction. Database unique constraints prevent races that an application-only pre-check cannot prevent.

Use migrations such as Alembic for schema changes. Add indexes based on real query patterns, avoid N+1 queries, and use stable ordering for pagination. Offset pagination is simple; cursor/keyset pagination can work better for large changing datasets. Prevent lost updates with version checks or conditional requests when needed. [FastAPI SQL tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/), [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

## 10. Authentication and authorization

Authentication establishes identity; authorization checks whether that identity can perform an action on a particular resource. A logged-in user must still be checked against note ownership.

`OAuth2PasswordBearer` extracts a bearer token and describes the security scheme; it does not independently validate the token or log in the user. Validate signatures and relevant claims, including expiry, issuer, and audience. A signed JWT is not encrypted: do not put secrets in its payload. Hash passwords with a dedicated password-hashing library, never plaintext storage. Keep signing keys out of source control and use HTTPS.

Discuss access-token lifetime, refresh-token handling, revocation, and scopes. For browser login, consider an identity provider and authorization code with PKCE; choose the flow for the client and threat model. [FastAPI security tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

## 11. Middleware and CORS

Middleware wraps requests/responses for concerns such as request IDs, timing, and logging. Avoid logging passwords or bearer tokens.

CORS controls whether browser JavaScript may access cross-origin responses; it is not authentication and does not stop curl or server-to-server requests. An origin includes scheme, host, and port. Configure explicit trusted origins, methods, and headers, especially with credentials. Browsers may send OPTIONS preflight requests. [CORS guide](https://fastapi.tiangolo.com/tutorial/cors/), [middleware guide](https://fastapi.tiangolo.com/tutorial/middleware/)

## 12. Background tasks and lifespan

`BackgroundTasks` can run small tasks after a response is sent. These tasks run within the application process; a crash can lose work. Use a durable external queue/worker system for important, lengthy, or retryable jobs. Do not carry a request-owned database session into a background job; create resources for the job. [Background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

Use the lifespan context manager for application startup/shutdown resources:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize shared clients/pools here.
    try:
        yield
    finally:
        # Close those clients/pools here.
        pass

app = FastAPI(lifespan=lifespan)
```

Lifespan is the recommended lifecycle approach; older startup/shutdown event handlers are the deprecated alternative. [Lifespan guide](https://fastapi.tiangolo.com/advanced/events/)

## 13. Testing

Use `TestClient` for ordinary synchronous API tests; it depends on HTTPX. Use it as a context manager when startup/shutdown behavior matters. For async tests, use an async client with ASGI transport and arrange lifespan handling when needed.

Test observable behavior: status codes, JSON, validation boundaries, missing IDs, pagination, permissions, and database effects. Use isolated data and reset dependency overrides. This repo specifically checks omitted PATCH fields, explicit null, false values, full replacement defaults, and an empty 204 response. [Testing guide](https://fastapi.tiangolo.com/tutorial/testing/), [async tests](https://fastapi.tiangolo.com/advanced/async-tests/)

## 14. Project structure and deployment

For a larger service, split route groups using `APIRouter` and register them with `include_router`. Keep validation schemas, persistence models, business services, and dependencies in focused modules. A single file is useful for learning; structure should follow actual complexity. [Bigger applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

Typical layout:

```text
app/
  main.py
  routers/notes.py
  schemas/note.py
  models/note.py
  services/notes.py
  dependencies.py
tests/
```

For deployment: disable development reload, provide environment-based settings, store secrets outside Git, configure HTTPS/proxy trust, and add health checks, logs, metrics, and error reporting. Multiple worker processes do not share Python dictionaries. Use a real database or shared cache. Size worker and database connection counts together. A container orchestrator may scale replicas instead of multiple workers per container. [Deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/)

## 15. Other topics worth being ready for

- **WebSockets:** long-lived bidirectional communication, disconnect handling, authentication, and shared messaging across processes. [WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- **Streaming:** send chunks without building the whole response; account for disconnects and resource lifetimes. [Response types](https://fastapi.tiangolo.com/advanced/custom-response/)
- **Caching:** keys must account for query parameters and user scope; plan invalidation and TTLs.
- **Rate limiting:** use shared state if limits must hold across workers; return useful retry information.
- **Settings:** `pydantic-settings` supports typed configuration from environment variables; never commit real credentials. [Settings](https://fastapi.tiangolo.com/advanced/settings/)
- **OpenAPI:** the generated API contract can support documentation and client generation, but business behavior still needs explanation. [OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/)

## 16. Rapid interview questions

| Question | Short answer |
| --- | --- |
| Does async always make an API faster? | No. It helps concurrent I/O; blocking calls can still stall the event loop. |
| Why separate input and output models? | Different contracts; prevent client writes to internal fields and accidental sensitive output. |
| Why use Depends? | Reuse prerequisites, manage resources, and substitute collaborators in tests. |
| What does 422 mean here? | Request data failed validation against the declared schema. |
| Is DELETE idempotent if the second call returns 404? | Yes. The resource remains absent after repeating it. |
| Is PATCH always idempotent? | No. Assignment can be; increment-style operations usually are not. |
| How do you prevent overwriting omitted PATCH fields? | Dump only fields supplied by the client with exclude_unset=True. |
| Does JWT validation prove access to every note? | No. Check resource-level authorization separately. |
| Can a global dictionary work with four workers? | Each process has its own dictionary; use persistent/shared storage. |
| Are background tasks a durable queue? | No. In-process work can be lost on failure. |
| Does response_model fix bad business logic? | No. It validates the output contract, not the correctness of the business operation. |
| How would you productionize this demo? | Add persistence, migrations, authentication, ownership checks, observability, and deployment configuration. |

## 17. Final revision checklist

- Explain the roles of FastAPI, Starlette, Pydantic, and Uvicorn.
- Run all five HTTP methods without copying the solution.
- Demonstrate PUT replacement and PATCH omission/null/false behavior.
- Explain 201, 204, 401, 403, 404, 409, and 422.
- Show dependency overrides and explain test isolation.
- Explain async I/O vs blocking I/O vs CPU work.
- Describe a database transaction and safe session lifecycle.
- Explain authentication, ownership checks, and why CORS is different.
- Describe how retries, concurrency, and multiple workers affect correctness.
- Explain which limitations in this demo you would address first for production.
