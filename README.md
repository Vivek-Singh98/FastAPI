# FastAPI

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
