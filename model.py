"""LSTM that predicts debris-flow risk from a window of sensor readings."""
import torch
import torch.nn as nn

FEATURES = ["soil_moisture", "tilt_deg", "vibration", "rainfall_mm_h", "fos"]


class DebrisFlowLSTM(nn.Module):
    def __init__(self, n_features: int = len(FEATURES), hidden: int = 64, layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, layers, batch_first=True, dropout=0.2)
        self.head = nn.Sequential(nn.Linear(hidden, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):                 # x: (batch, time, features)
        out, _ = self.lstm(x)
        return torch.sigmoid(self.head(out[:, -1]))   # probability of failure within the horizon
