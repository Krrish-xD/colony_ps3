## Pass 1 Review
- Issues Found
  1. The code catches `docker.errors.NotFound`, but `docker` also throws `docker.errors.APIError` and others if Docker is unreachable or the command fails. We should handle broader docker API errors gracefully so the service doesn't crash or return 500 when we expect to return 500 but without crashing. Actually, FastAPI handles 500s nicely, but we should make sure the logging is clean.
  2. Sub-100ms execution time: The endpoint is async, but the docker restart command is synchronous. This could block the event loop. Given the hackathon constraints and low load, a synchronous endpoint might actually be better to avoid async/sync mismatches, or we could use `def` instead of `async def` for the endpoint so FastAPI runs it in a threadpool automatically.
  3. Payload validation check: `confidence` is required to be a float, but what if it's sent as a string or an int? Pydantic handles int to float conversion. That's fine.
  4. Docker socket initialization: `client = docker.from_env()` is synchronous and might fail on startup if the socket is not immediately available. It might be better to initialize or re-initialize it lazily if it fails on startup.
- Why they are problems
  1. The event loop could be blocked by synchronous `docker.restart()`, preventing the sub-100ms response time for concurrent requests.
  2. If the docker daemon restarts or connection drops, `client = docker.from_env()` initialized only on startup might become stale. It's better to instantiate it globally but gracefully handle its usage.
- Fixes to apply
  1. Change `async def handle_action` to `def handle_action` so FastAPI runs the synchronous Docker operation in a thread pool, preventing event loop blocking.
  2. Ensure we check if `client` is valid, and handle `docker.errors.APIError`.
  3. Add a lazy initialization of the docker client just in case it wasn't ready at startup.
