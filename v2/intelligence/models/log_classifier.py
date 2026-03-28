import torch
import torch.nn.functional as F

class ZeroShotLogClassifier:
    def __init__(self, embedding_model, device):
        self.embedding_model = embedding_model
        self.device = device

        # Expanded predefined categories and their descriptions based on the v2 architecture
        self.categories = {
            "db_connection_exhaustion": "Connection pool drained, postgres refused, database connection timeout, no available connections.",
            "memory_pressure": "Out of memory, OOM, memory leak patterns, heap space limit, garbage collection overhead.",
            "upstream_timeout": "Downstream service timed out causing upstream cascade, slow response, gateway timeout, 504.",
            "crash_injection": "os._exit(1) called, hard crash, container dies instantly, segmentation fault, panic.",
            "disk_io_saturation": "Slow disk, I/O wait patterns, high input/output latency, disk full, no space left on device.",
            "connection_refused": "Network unreachable, service down, connection reset by peer, connection closed abruptly.",
            "authentication_failure": "Invalid token, unauthorized, 401, signature verification failed, expired credentials.",
            "rate_limiting": "Too many requests, 429, rate limit exceeded, quota exhausted, throttling applied.",
            "data_corruption": "Checksum mismatch, corrupted payload, invalid JSON, unable to parse data.",
            "dependency_failure": "Third-party API failed, external dependency down, payment gateway unreachable.",
            "normal_degradation": "Slight slowdown, not critical, request taking longer than usual but completing.",
            "normal": "Normal operation, request processed successfully, health check ok, starting service."
        }

        self.category_names = list(self.categories.keys())
        self.category_descriptions = list(self.categories.values())

        # Precompute embeddings for the category descriptions
        self.category_embeddings = self._embed(self.category_descriptions)

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

        # If the highest similarity is below a strong threshold, it's an unseen, novel error pattern.
        # This prevents the model from confidently guessing the wrong category when given totally unrelated logs.
        UNKNOWN_THRESHOLD = 0.45
        if max_sim < UNKNOWN_THRESHOLD:
            return "unknown", max_prob.item()

        return self.category_names[max_idx.item()], max_prob.item()
