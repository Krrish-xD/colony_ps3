import torch
import torch.nn as nn

ROOT_CAUSE_CLASSES = [
    "db_connection_exhaustion",     # Connection pool drained, postgres refused
    "memory_pressure",              # OOM, memory leak patterns
    "upstream_timeout",             # Downstream service timed out causing upstream cascade
    "crash_injection",              # os._exit(1) called — hard crash
    "disk_io_saturation",           # Slow disk, I/O wait patterns
    "connection_refused",           # Network unreachable, service down
    "normal_degradation",           # Slight slowdown, not critical
    "unknown"                       # Low confidence, can't classify
]

class FusionClassifier(nn.Module):
    """
    Multi-signal fusion classifier.
    Input: concatenation of log_embedding (384) + metric_features (8) + trace_features (6) = 398
    Output: softmax probabilities over 8 root cause classes
    """
    def __init__(self, input_dim=398, num_classes=8):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        return self.network(x)

def classify(log_embedding, metric_features, trace_features, model, device='cuda'):
    features = log_embedding + metric_features + trace_features  # concatenate lists
    tensor = torch.FloatTensor(features).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        confidence, predicted = torch.max(probs, 1)
    return ROOT_CAUSE_CLASSES[predicted.item()], confidence.item(), probs[0].tolist()
