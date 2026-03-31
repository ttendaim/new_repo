import pandas as pd

def run():
    """Sample data pipeline - returns a DataFrame."""
    data = {
        "user_id": [1, 2, 3],
        "email": ["a@example.com", "b@example.com", "c@example.com"],
        "created_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        "amount": [100.0, 200.0, 300.0],
    }
    return pd.DataFrame(data)

if __name__ == "__main__":
    print(run())
    print('Small change to test PR')