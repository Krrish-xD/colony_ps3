import os
import glob
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sentence_transformers import SentenceTransformer

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.fusion_classifier import FusionClassifier, ROOT_CAUSE_CLASSES
from main import extract_metric_features, extract_trace_features

DATA_DIR = "/app/data/training_samples"
WEIGHTS_PATH = "/app/weights/fusion_model.pt"

print("Loading SentenceTransformer...")
embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cuda' if torch.cuda.is_available() else 'cpu')

def load_dataset():
    files = glob.glob(f"{DATA_DIR}/*.json")
    if not files:
        print(f"No training data found in {DATA_DIR}!")
        return None, None
        
    X_list, y_list = [], []
    for f in files:
        with open(f, 'r') as file:
            data = json.load(file)
            
        label = data["label"]
        if label not in ROOT_CAUSE_CLASSES: continue
        label_idx = ROOT_CAUSE_CLASSES.index(label)
        
        # Extract features
        log_feats = embedder.encode(data.get("logs", [""])).mean(axis=0).tolist()
        met_feats = extract_metric_features(data.get("metrics", []))
        trc_feats = extract_trace_features(data.get("traces", []))
        
        combined = log_feats + met_feats + trc_feats
        X_list.append(combined)
        y_list.append(label_idx)
        
    return torch.FloatTensor(X_list), torch.LongTensor(y_list)

def train():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    X, y = load_dataset()
    if X is None: return
    
    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)
    
    model = FusionClassifier().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    model.train()
    print("Starting Training Loop...")
    for epoch in range(1, 51):
        total_loss = 0
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        if epoch % 10 == 0:
            print(f"Epoch {epoch}/50 | Loss: {total_loss/len(loader):.4f}")
            
    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    torch.save(model.state_dict(), WEIGHTS_PATH)
    print(f"Model saved to {WEIGHTS_PATH}")

if __name__ == "__main__":
    train()
