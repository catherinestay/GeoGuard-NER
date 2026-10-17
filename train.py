"""Train the LSTM on SYNTHETIC data. Replace make_dataset() with real field logs."""
import numpy as np
import torch
import torch.nn as nn
from fos import factor_of_safety
from model import DebrisFlowLSTM

SEQ_LEN = 72          # e.g. 72 hourly samples = 72 hours
rng = np.random.default_rng(0)


def make_dataset(n=2000):
    X, y = [], []
    for _ in range(n):
        slope = rng.uniform(20, 45)
        rain = np.clip(np.cumsum(rng.normal(0, 3, SEQ_LEN)) + rng.uniform(0, 20), 0, 80)
        soil = np.clip(np.convolve(rain / 80, np.ones(12) / 12, mode="same") + rng.normal(0, 0.03, SEQ_LEN), 0, 1)
        tilt = slope * 0.02 + np.cumsum(soil > 0.8) * 0.01 + rng.normal(0, 0.05, SEQ_LEN)
        vib = np.abs(rng.normal(0, 0.01, SEQ_LEN)) + (soil > 0.85) * 0.02
        fos = np.array([factor_of_safety(slope, s) for s in soil])
        X.append(np.stack([soil, tilt, vib, rain / 80, fos / 3], axis=1))
        y.append(float(fos[-1] < 1.2))
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(y).unsqueeze(1)


def main():
    X, y = make_dataset()
    split = int(0.8 * len(X))
    model = DebrisFlowLSTM()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCELoss()
    for epoch in range(10):
        model.train()
        perm = torch.randperm(split)
        for i in range(0, split, 64):
            idx = perm[i:i + 64]
            opt.zero_grad()
            loss = loss_fn(model(X[idx]), y[idx])
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            acc = ((model(X[split:]) > 0.5).float() == y[split:]).float().mean().item()
        print(f"epoch {epoch + 1:2d}  loss {loss.item():.4f}  val acc {acc:.3f}")
    torch.save(model.state_dict(), "debris_lstm.pt")


if __name__ == "__main__":
    main()
