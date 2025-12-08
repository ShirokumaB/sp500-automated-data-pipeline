# S&P 500 Index (^GSPC) Automated Data Pipeline

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-ff4b4b)
![Status](https://img.shields.io/badge/Status-Active-success)

This project is a **Full-Stack Data Engineering Solution** designed to automate the lifecycle of financial data for the S&P 500 Index. It demonstrates a robust pipeline that fetches, cleans, validates, and visualizes market data using a modern tech stack.

An automated data engineering pipeline that fetches **S&P 500 Index (^GSPC)** data daily, processes technical indicators, stores them in a database, and visualizes trading strategy performance via an interactive dashboard.

## 📺 Demo & Validation

This project includes a **Streamlit Dashboard** (`dashboard.py`) that serves as a live document and validation tool.
*   **Live Data View:** Visualizes the latest data fetched by the pipeline.
*   **Strategy Check:** Runs a basic SMA Crossover backtest to prove data integrity and usability.
*   **Project Documentation:** Contains an in-app "About" page explaining the architecture.

*(Screenshot or GIF of the dashboard would go here)*

## 🚀 Features

*   **Automated ETL Pipeline:** Orchestrated by **Prefect** to fetch data daily.
*   **S&P 500 Index Data:** Specifically targets the `^GSPC` ticker.
*   **Data Processing:** Cleans raw data and calculates Moving Averages (MA 20, 50, 100, 200).
*   **Database Integration:** specific storage in **PostgreSQL**.
*   **Interactive Dashboard:** Built with **Streamlit** to visualize stock prices and backtest strategies.
*   **Backtesting Engine:** Uses **VectorBT** to simulate SMA Crossover strategies.

## 🛠 Tech Stack

*   **Orchestration:** Prefect
*   **Data Source:** Yahoo Finance (`yfinance`)
*   **Database:** PostgreSQL
*   **Visualization:** Streamlit, Matplotlib
*   **Analysis:** Pandas, NumPy, VectorBT

## 📂 Project Structure

```
├── sp500_pipeline.py    # Main ETL logic (Extract -> Transform -> Load)
├── deploy_pipeline.py   # Prefect deployment and scheduling configuration
├── dashboard.py         # Streamlit application for visualization using data from DB
├── notebooks/           # Jupyter notebooks for research and backtest experiments
└── .env.example        # Template for environment variables
```

## ☁️ Deployment (How to Share)

To verify this project publicly, you can deploy it for free using **Streamlit Community Cloud**:

1.  Push this code to a **GitHub Repository**.
2.  Go to [share.streamlit.io](https://share.streamlit.io/).
3.  Connect your GitHub and select this repository.
4.  **Important:** In the "Advanced Settings" of the deployment, you must add your Database credentials as **Secrets** (matching content in `.env`).
    *   *Note: Since this project uses a local PostgreSQL, for a public demo, you would typically migrate the DB to a cloud provider (e.g., Supabase, Neon) or use an SQLite file for simplicity in demos.*

## ⚡ Getting Started (Local)

### Prerequisites

*   Python 3.9+
*   PostgreSQL Database
*   Prefect Account (optional for cloud, required for some features)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/sp500-pipeline.git
    cd sp500-pipeline
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If `requirements.txt` is missing, you'll need `prefect`, `pandas`, `yfinance`, `sqlalchemy`, `psycopg2-binary`, `streamlit`, `vectorbt`, `python-dotenv`)*

3.  Set up Environment Variables:
    Create a `.env` file in the root directory:
    ```env
    DB_USER=your_user
    DB_PASSWORD=your_password
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=your_db_name
    ```

### Usage

**1. Run the Pipeline Manually:**
```bash
python sp500_pipeline.py
```

**2. Deploy the Pipeline (Schedule):**
```bash
python deploy_pipeline.py
```

**3. Launch the Dashboard:**
```bash
streamlit run dashboard.py
```

## 📊 Dashboard Preview

The dashboard allows you to:
*   Select a stock ticker (currently focused on S&P 500).
*   Choose a strategy (e.g., SMA Crossover).
*   Adjust parameters (Short/Long windows).
*   View performance metrics (Sharpe Ratio, Max Drawdown, Total Return).

## 🔮 Future Improvements

*   [ ] Containerize with Docker & Docker Compose.
*   [ ] Deploy database to Cloud (AWS RDS/GCP SQL).
*   [ ] Add email/Slack notifications for buy/sell signals.
*   [ ] Implement data quality tests (Great Expectations).

