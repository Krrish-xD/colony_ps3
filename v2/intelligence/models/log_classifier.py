import torch
import torch.nn.functional as F

class ZeroShotLogClassifier:
    def __init__(self, embedding_model, device):
        self.embedding_model = embedding_model
        self.device = device

        # Predefined categories and their descriptions based on the v2 architecture
        self.categories = {
            "db_connection_exhaustion": "Connection pool drained, postgres refused, database connection timeout.",
            "memory_pressure": "Out of memory, OOM, memory leak patterns, heap space limit.",
            "upstream_timeout": "Downstream service timed out causing upstream cascade, slow response.",
            "crash_injection": "os._exit(1) called, hard crash, container dies instantly.",
            "disk_io_saturation": "Slow disk, I/O wait patterns, high input/output latency.",
            "connection_refused": "Network unreachable, service down, connection reset by peer.",
            "normal_degradation": "Slight slowdown, not critical, request taking longer than usual.",
            "normal": "Normal operation, request processed successfully, starting service."
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

        return self.category_names[max_idx.item()], max_prob.item()
