import torch
import torch.nn as nn
import json
import os

# Updated to reflect the granular Resource vs Code failure states
ROOT_CAUSE_CLASSES = [
    "cpu_starvation",               # Maps to CPU quota scale actions
    "memory_pressure",              # Maps to memory bound scale actions
    "upstream_timeout",             # Downstream service timeout
    "connection_refused",           # Network unreachability
    "crash_injection",              # Hard fast failure
    "normal_degradation",
    "unknown"
]

class FusionClassifier(nn.Module):
    """
    Multi-signal fusion classifier for Colony PS3 v3.
    Inputs:
      - Log Embedding (SentenceTransformer all-MiniLM-L6-v2): 384 dims
      - Metric Features (numpy statistical extraction): 8 dims
      - Trace Features (Jaeger span rollups): 6 dims
    Total Input Dimension: 398
    """
    def __init__(self, input_dim=398, num_classes=len(ROOT_CAUSE_CLASSES)):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        return self.network(x)

def classify(log_embedding: list[float], metric_features: list[float], trace_features: list[float], model: nn.Module, device='cuda'):
    """Helper method to process raw feature arrays through the active model."""
    features = log_embedding + metric_features + trace_features  # flat list of 398 floats
    tensor = torch.FloatTensor(features).unsqueeze(0).to(device)
    
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        confidence, predicted_idx = torch.max(probs, 1)
        
    class_idx = predicted_idx.item()
    return ROOT_CAUSE_CLASSES[class_idx], confidence.item(), probs[0].tolist()

def load_model(weights_path: str = "/app/weights/fusion_model.pt", device='cuda') -> nn.Module:
    """Instantiate and load pre-trained weights if available."""
    model = FusionClassifier()
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location=device))
        print(f"[Fusion] Loaded weights from {weights_path}")
    else:
        print("[Fusion] Warning: No trained weights found. Using random initialization.")
    
    model.to(device)
    model.eval()
    return model
