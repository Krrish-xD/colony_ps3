## Pass 1 Review

- **Issues Found**:
  1. The Webhook payload labels might use `compose_service`, `app`, or `service` to denote the service. Our extraction was restricted to `service`.
  2. The Master Guide mentions a fallback mechanism for when Loki logs return 0 results (service hung, cannot write stdout): "The RCA engine falls back to traces. It queries Jaeger for the Frontend trace and traverses the causal graph to find the exact span that dropped the connection, marking the root cause as "Upstream Timeout" instead of "Internal Exception"."
  3. No HTTP timeouts configured on outward calls.
- **Why they are problems**:
  1. If labels are different based on OTel config, RCA will fail silently because `service_name` will be None.
  2. A completely crashed service wouldn't print error logs; relying solely on Loki log ingestion leaves an RCA gap during deep hangs.
  3. Without HTTP timeouts, calling unavailable services (e.g. Jaeger or Loki) could delay remediation past the 15-second strict budget.
- **Fixes applied**:
  1. Expanded webhook label lookup to check `service`, `compose_service`, and `app`.
  2. Implemented a Jaeger trace API check if `logs_found` remains `False`, correctly adjusting `root_cause` to `Upstream Timeout` with 0.85 confidence as mandated by the guide.
  3. Added low timeout values (1-2s) to `httpx.AsyncClient` requests to guarantee quick failure over unbounded blocking.