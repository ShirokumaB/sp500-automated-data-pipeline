import yfinance as yf
import pandas as pd

def fetch_and_save():
    print("Fetching full S&P 500 history...")
    # Fetch max history
    df = yf.download("^GSPC", period="max", interval="1d")
    
    # Flatten columns if multi-index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    
    df.reset_index(inplace=True)
    df.rename(columns={"Date": "date"}, inplace=True)
    
    # Save to the github upload folder
    output_path = "sp500_market_data.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")

if __name__ == "__main__":
    fetch_and_save()
