"""Script to train Isolation Forest anomaly detection model for the fraud engine."""
import os
import pickle
import numpy as np
from sklearn.ensemble import IsolationForest

def train_and_save_model(output_path: str = "app/models/fraud_model.pkl"):
    print("Training Isolation Forest fraud anomaly model...")
    # Seed for determinism
    np.random.seed(42)

    # 1. Normal transactions: amounts mostly between 100 and 50,000 INR (10,000 to 5,000,000 minor)
    # velocity 1 to 5 per hour
    n_normal = 2000
    normal_amounts = np.random.exponential(scale=200000, size=n_normal) + 50000
    normal_velocity = np.random.poisson(lam=2, size=n_normal) + 1
    normal_data = np.column_stack([normal_amounts, normal_velocity])

    # 2. Anomalous transactions: very high amounts or huge velocity
    n_anomalous = 100
    anom_amounts = np.random.uniform(5000000, 50000000, size=n_anomalous)
    anom_velocity = np.random.uniform(15, 60, size=n_anomalous)
    anom_data = np.column_stack([anom_amounts, anom_velocity])

    X = np.vstack([normal_data, anom_data])

    clf = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    clf.fit(X)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(clf, f)

    print(f"Model successfully saved to {output_path}")

if __name__ == "__main__":
    model_path = os.getenv("FRAUD_MODEL_PATH", "backend/app/models/fraud_model.pkl")
    train_and_save_model(model_path)
