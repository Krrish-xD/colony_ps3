import torch
import torch.nn as nn
import numpy as np

class MetricLSTM(nn.Module):
    """
    Tiny LSTM for metric anomaly detection.
    Input: sequence of 60 metric values (1 per second, last 60s)
    Output: predicted next 5 values
    """
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, prediction_length=5):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, prediction_length)

    def forward(self, x):
        # x shape: (batch, seq_len, 1)
        lstm_out, _ = self.lstm(x)
        prediction = self.fc(lstm_out[:, -1, :])  # Use last hidden state
        return prediction

def detect_anomaly(actual_values, predicted_values, threshold_sigma=3.0):
    """Compare actual vs predicted. If deviation > threshold standard deviations, flag anomaly."""
    residuals = np.abs(np.array(actual_values) - np.array(predicted_values))
    mean_residual = np.mean(residuals)
    std_residual = np.std(residuals) + 1e-8
    z_scores = (residuals - mean_residual) / std_residual
    # If any of the 5 predictions deviate by > 3 sigma, it's anomalous
    is_anomalous = bool(np.any(z_scores > threshold_sigma))
    max_deviation = float(np.max(z_scores))
    return is_anomalous, max_deviation

import os

# Load LSTM model once at module level
device = 'cuda' if torch.cuda.is_available() else 'cpu'
lstm_model_instance = MetricLSTM()
if os.path.exists("/app/weights/lstm_model.pt"):
    lstm_model_instance.load_state_dict(torch.load("/app/weights/lstm_model.pt", map_location=device))
lstm_model_instance.to(device)
lstm_model_instance.eval()

def lstm_predict_and_check(service, metrics):

    # Extract raw values
    values = np.array([float(v) for _, v in metrics])
    if len(values) < 60:
        return False, 0.0

    input_seq = values[-60:]

    # Normalize (z-score)
    mean = np.mean(input_seq)
    std = np.std(input_seq) + 1e-8
    input_norm = (input_seq - mean) / std

    tensor_input = torch.FloatTensor(input_norm).unsqueeze(0).unsqueeze(-1).to(device)

    with torch.no_grad():
        pred_norm = lstm_model_instance(tensor_input).cpu().numpy()[0]

    pred = pred_norm * std + mean

    # We compare with last 5 if possible, but actually predict_and_check needs actuals.
    # The requirement says "If anomaly detected -> log it".
    # Since we are predicting the *next* 5 values, we don't have actuals yet.
    # The requirement likely implies comparing prediction with actuals once we have them,
    # or just predicting and using a different check. The simplest is to assume we compare
    # a rolling window.
    # We will use the last 5 values of the *current* sequence as a dummy 'actual' just to satisfy
    # the function signature if needed, or we just return an anomaly based on how far pred is from current mean.

    # Let's adjust detect_anomaly logic slightly to fit typical usage:
    # We predict 5 steps ahead.
    # A simple threshold: if the prediction deviates wildly from recent history

    recent_mean = np.mean(input_seq[-5:])
    recent_std = np.std(input_seq[-5:]) + 1e-8

    z_scores = np.abs(pred - recent_mean) / recent_std
    is_anomalous = bool(np.any(z_scores > 3.0))
    max_deviation = float(np.max(z_scores))

    return is_anomalous, max_deviation
