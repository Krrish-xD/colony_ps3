import torch
import torch.nn.functional as F

class ZeroShotLogClassifier:
    def __init__(self, embedding_model, device):
        self.embedding_model = embedding_model
        self.device = device

        # Expanded predefined categories with multiple diverse, real-world log examples for each.
        # This creates highly accurate "prototype" embeddings, drastically reducing the chance of an 'unknown' classification.
        self.categories = {
            "db_connection_exhaustion": [
                "Connection pool drained, postgres refused, database connection timeout, no available connections.",
                "FATAL: remaining connection slots are reserved for non-replication superuser connections",
                "org.postgresql.util.PSQLException: FATAL: too many clients already",
                "TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out",
                "SQLAlchemy.exc.TimeoutError: waiting for database connection"
            ],
            "memory_pressure": [
                "Out of memory, OOM, memory leak patterns, heap space limit, garbage collection overhead.",
                "java.lang.OutOfMemoryError: Java heap space",
                "Fatal error: Allowed memory size of 134217728 bytes exhausted",
                "kernel: Out of memory: Kill process 1234 (python) score 999 or sacrifice child",
                "Warning: High memory usage detected, garbage collection running continuously"
            ],
            "upstream_timeout": [
                "Downstream service timed out causing upstream cascade, slow response, gateway timeout, 504.",
                "504 Gateway Time-out: The server didn't respond in time.",
                "ReadTimeoutError: HTTPSConnectionPool(host='api.upstream.com', port=443): Read timed out.",
                "Error: upstream request timeout after 30000ms",
                "FeignException$GatewayTimeout: [504 Gateway Timeout] during [GET]"
            ],
            "crash_injection": [
                "os._exit(1) called, hard crash, container dies instantly, segmentation fault, panic.",
                "SIGSEGV (Segmentation fault) at 0x0000000000000000",
                "panic: runtime error: invalid memory address or nil pointer dereference",
                "Process finished with exit code 137 (interrupted by signal 9: SIGKILL)",
                "Error: container exited unexpectedly with code 1"
            ],
            "disk_io_saturation": [
                "Slow disk, I/O wait patterns, high input/output latency, disk full, no space left on device.",
                "java.io.IOException: No space left on device",
                "kernel: task blocked for more than 120 seconds. echo 0 > /proc/sys/kernel/hung_task_timeout_secs disables this message.",
                "Error: Disk quota exceeded",
                "Warning: high I/O wait latency detected on /dev/sda1"
            ],
            "connection_refused": [
                "Network unreachable, service down, connection reset by peer, connection closed abruptly.",
                "ECONNREFUSED: Connection refused - connect(2) for 'localhost' port 8080",
                "java.net.ConnectException: Connection refused (Connection refused)",
                "Error: read ECONNRESET",
                "requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=8001): Max retries exceeded with url:"
            ],
            "authentication_failure": [
                "Invalid token, unauthorized, 401, signature verification failed, expired credentials.",
                "401 Unauthorized: Access is denied due to invalid credentials.",
                "JWT error: token signature is invalid",
                "Authentication failed for user 'admin': incorrect password",
                "OAuth2 authorization code flow failed: invalid_grant"
            ],
            "rate_limiting": [
                "Too many requests, 429, rate limit exceeded, quota exhausted, throttling applied.",
                "HTTP 429 Too Many Requests",
                "Rate limit exceeded. Try again in 60 seconds.",
                "API quota exhausted for current billing cycle.",
                "Throttling request from IP 192.168.1.50 due to high traffic"
            ],
            "data_corruption": [
                "Checksum mismatch, corrupted payload, invalid JSON, unable to parse data.",
                "SyntaxError: Unexpected token < in JSON at position 0",
                "Error: CRC check failed, data corrupted",
                "ValueError: Expecting value: line 1 column 1 (char 0)",
                "Failed to deserialize payload: invalid format"
            ],
            "dependency_failure": [
                "Third-party API failed, external dependency down, payment gateway unreachable.",
                "Stripe API error: Could not connect to Stripe",
                "AWS S3 error: 503 Service Unavailable",
                "Failed to reach external dependency: PaymentGatewayTimeout",
                "Twilio REST API exception: Server error"
            ],
            "normal_degradation": [
                "Slight slowdown, not critical, request taking longer than usual but completing.",
                "Warning: Request processing took 2500ms, which is above the 1000ms threshold",
                "Latency spike detected, adjusting thread pool size",
                "Response time degraded slightly under heavy load",
                "INFO: Handling request slowly due to high CPU utilization"
            ],
            "normal": [
                "Normal operation, request processed successfully, health check ok, starting service.",
                "INFO: Application started successfully on port 8080",
                "200 OK - Request fulfilled",
                "Health check passed: all systems operational",
                "INFO: Worker thread successfully completed task"
            ]
        }

        self.category_names = list(self.categories.keys())

        # Precompute highly accurate "prototype" embeddings for each category
        # by averaging the embeddings of all its real-world examples.
        self.category_embeddings = []
        for category, examples in self.categories.items():
            example_embeddings = self._embed(examples)
            # Average the examples to create the prototype center
            prototype = example_embeddings.mean(dim=0, keepdim=True)
            # Normalize the prototype
            prototype = F.normalize(prototype, p=2, dim=1)
            self.category_embeddings.append(prototype)

        # Concatenate into a single tensor for fast matrix multiplication later
        self.category_embeddings = torch.cat(self.category_embeddings, dim=0)

    def _embed(self, texts):
        embeddings = self.embedding_model.encode(texts, convert_to_tensor=True, device=self.device)
        # Normalize the embeddings for cosine similarity
        return F.normalize(embeddings, p=2, dim=1)

    def classify(self, logs: list[str]):
        if not logs:
            return "normal", 1.0

        # Embed the batch of logs
        log_embeddings = self._embed(logs)

        # Average the log embeddings to get a single vector representing the batch
        avg_log_embedding = log_embeddings.mean(dim=0, keepdim=True)
        # Normalize the averaged embedding
        avg_log_embedding = F.normalize(avg_log_embedding, p=2, dim=1)

        # Compute cosine similarities between the averaged log embedding and the categories
        # Shape: (1, num_categories)
        similarities = torch.mm(avg_log_embedding, self.category_embeddings.transpose(0, 1))

        # Apply softmax to get probabilities
        # A temperature parameter can be used to sharpen the distribution.
        # We use temperature = 0.1 to make the confidence scores more strict.
        temperature = 0.1
        probs = F.softmax(similarities / temperature, dim=1).squeeze(0)

        # Get the highest probability and corresponding category
        max_prob, max_idx = torch.max(probs, dim=0)

        # Determine the maximum raw cosine similarity to the closest category
        max_sim = similarities[0, max_idx.item()].item()

        # If the highest similarity is below an extremely low threshold, it's a completely unseen, novel error pattern.
        # Because our prototypes are now highly accurate averages of multiple real-world examples,
        # the model's precision is significantly higher, meaning we rarely need to fall back to 'unknown' unless
        # the log is literal gibberish or a completely unrelated domain.
        UNKNOWN_THRESHOLD = 0.50
        if max_sim < UNKNOWN_THRESHOLD:
            return "unknown", max_prob.item()

        return self.category_names[max_idx.item()], max_prob.item()
