import torch
import torch.nn as nn
import numpy as np

class MetricLSTM(nn.Module):
    """
    Predictive Metric Forecaster for Colony PS3 v3.
    Ingests the last 60 seconds of Prometheus HTTP duration metrics.
    Outputs the expected latency values for the next 5 seconds.
    """
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, prediction_length=5):
        super().__init__()
        self.prediction_length = prediction_length
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2 if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_size, prediction_length)

    def forward(self, x):
        # x expected shape: (batch_size, seq_len=60, features=1)
        lstm_out, (hn, cn) = self.lstm(x)
        # Take the output from the last time step to predict the future sequence
        prediction = self.fc(lstm_out[:, -1, :])
        return prediction

def detect_anomaly(actual_values: list[float], predicted_values: list[float], threshold_sigma: float = 3.0) -> tuple[bool, float]:
    """
    Evaluates actual real-time telemetry against the model's 5s historical prediction.
    If the actual values deviate by more than threshold_sigma, flags an anomaly.
    This triggers proactive upscaling BEFORE the entire system crashes.
    """
    if len(actual_values) != len(predicted_values):
        raise ValueError("Actual and predicted sequences must match in length.")
        
    residuals = np.abs(np.array(actual_values) - np.array(predicted_values))
    
    # Ideally, standard deviation would be computed across a much larger historical baseline.
    # For sub-15s hackathon latency, we evaluate the micro-deviation burst.
    mean_residual = np.mean(residuals)
    std_residual = np.std(residuals) + 1e-8
    
    z_scores = (residuals - mean_residual) / std_residual
    
    max_z = float(np.max(z_scores))
    is_anomalous = bool(max_z > threshold_sigma)
    
    return is_anomalous, max_z
