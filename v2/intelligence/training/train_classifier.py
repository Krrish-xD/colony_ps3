import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer
import sys

# Add intelligence to path so we can import from models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.fusion_classifier import FusionClassifier, ROOT_CAUSE_CLASSES

DATA_DIR = "/app/training/data/" if __name__ == "__main__" else "/home/xd/Coding/colony_ps3/v2/intelligence/training/data/"
WEIGHTS_DIR = "/app/weights/" if __name__ == "__main__" else "/home/xd/Coding/colony_ps3/v2/intelligence/weights/"

def embed_logs(model, log_messages: list[str]) -> list[float]:
    if not log_messages:
        return [0.0] * 384
    embeddings = model.encode(log_messages, convert_to_numpy=True)
    return embeddings.mean(axis=0).tolist()

def extract_metric_features(metric_values: list[list]) -> list[float]:
    if not metric_values:
        return [0.0] * 8
    values = np.array([float(v[1]) for v in metric_values])
    return [
        float(np.mean(values)),
        float(np.std(values)),
        float(np.polyfit(range(len(values)), values, 1)[0]) if len(values) > 1 else 0.0,
        float(np.max(values) - np.min(values)),
        float(np.percentile(values, 50)),
        float(np.percentile(values, 95)),
        float(np.min(values)),
        float(np.max(values)),
    ]

def extract_trace_features(spans: list[dict]) -> list[float]:
    if not spans:
        return [0.0] * 6
    durations = [s.get('duration_us', 0) / 1000.0 for s in spans]
    errors = [s for s in spans if isinstance(s.get('status_code'), int) and s.get('status_code', 200) >= 400]
    return [
        float(np.mean(durations)),
        len(errors) / max(len(spans), 1),
        1.0,
        float(len(errors)),
        float(len(spans)),
        float(np.max(durations)) if durations else 0.0,
    ]

def load_data():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading data on {device}...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

    features = []
    labels = []

    if not os.path.exists(DATA_DIR):
        print(f"No data dir found at {DATA_DIR}")
        return [], []

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename), 'r') as f:
                data = json.load(f)

            label = data.get("label")
            if label not in ROOT_CAUSE_CLASSES:
                label = "unknown"

            label_idx = ROOT_CAUSE_CLASSES.index(label)

            logs_emb = embed_logs(embedding_model, data.get("logs", []))
            mets_feat = extract_metric_features(data.get("metrics", []))
            trc_feat = extract_trace_features(data.get("traces", []))

            combined = logs_emb + mets_feat + trc_feat
            features.append(combined)
            labels.append(label_idx)

    return np.array(features), np.array(labels)

def train():
    os.makedirs(WEIGHTS_DIR, exist_ok=True)

    features, labels = load_data()
    if len(features) == 0:
        print("No training data found. Please run generate_training_data.py first.")
        return

    X_train, X_val, y_train, y_val = train_test_split(features, labels, test_size=0.2, random_state=42)

    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_val_t = torch.FloatTensor(X_val)
    y_val_t = torch.LongTensor(y_val)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = FusionClassifier().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    print("Training Fusion Classifier...")
    model.train()
    for epoch in range(100):
        X_batch = X_train_t.to(device)
        y_batch = y_train_t.to(device)

        optimizer.zero_grad()
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/100], Loss: {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        outputs = model(X_val_t.to(device))
        _, predicted = torch.max(outputs.data, 1)
        correct = (predicted == y_val_t.to(device)).sum().item()
        acc = correct / len(y_val_t)
        print(f"Validation Accuracy: {acc * 100:.2f}%")

    torch.save(model.state_dict(), os.path.join(WEIGHTS_DIR, "fusion_model.pt"))
    with open(os.path.join(WEIGHTS_DIR, "classes.json"), "w") as f:
        json.dump(ROOT_CAUSE_CLASSES, f)
    print("Saved fusion_model.pt and classes.json")

if __name__ == "__main__":
    train()
