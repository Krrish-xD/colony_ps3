import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import sys

# Add intelligence to path so we can import from models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.lstm_detector import MetricLSTM

DATA_DIR = "/app/training/data/" if __name__ == "__main__" else "/home/xd/Coding/colony_ps3/v2/intelligence/training/data/"
WEIGHTS_DIR = "/app/weights/" if __name__ == "__main__" else "/home/xd/Coding/colony_ps3/v2/intelligence/weights/"

def load_data():
    sequences = []

    if not os.path.exists(DATA_DIR):
        print(f"No data dir found at {DATA_DIR}")
        return []

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename), 'r') as f:
                data = json.load(f)

            metrics = data.get("metrics", [])
            values = [float(v[1]) for v in metrics]
            if len(values) >= 65:
                sequences.append(values)

    return sequences

def create_windows(sequences, window_size=60, pred_size=5):
    X = []
    y = []

    for seq in sequences:
        for i in range(len(seq) - window_size - pred_size + 1):
            window = seq[i:i+window_size]
            target = seq[i+window_size:i+window_size+pred_size]

            # Normalize window
            mean = np.mean(window)
            std = np.std(window) + 1e-8

            window_norm = (np.array(window) - mean) / std
            target_norm = (np.array(target) - mean) / std

            X.append(window_norm)
            y.append(target_norm)

    return np.array(X), np.array(y)

def train():
    os.makedirs(WEIGHTS_DIR, exist_ok=True)

    sequences = load_data()
    if len(sequences) == 0:
        print("No training data found or sequences too short. Please run generate_training_data.py first.")
        return

    X, y = create_windows(sequences)

    X_t = torch.FloatTensor(X).unsqueeze(-1)  # (batch, seq, 1)
    y_t = torch.FloatTensor(y)  # (batch, pred)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = MetricLSTM().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    print("Training LSTM Detector...")
    model.train()
    epochs = 200
    for epoch in range(epochs):
        X_batch = X_t.to(device)
        y_batch = y_t.to(device)

        optimizer.zero_grad()
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 20 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")

    torch.save(model.state_dict(), os.path.join(WEIGHTS_DIR, "lstm_model.pt"))
    print("Saved lstm_model.pt")

if __name__ == "__main__":
    train()
