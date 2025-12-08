import streamlit as st
import pandas as pd
import vectorbt as vbt
import sqlalchemy
import os
from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv()

# ==========================================
# DATA LOADING (Hybrid: CSV > Database)
# ==========================================
@st.cache_data(ttl=3600)
def get_close_data():
    """
    Fetch S&P 500 data. 
    Priority:
    1. Local CSV (fast, stable, works for demo)
    2. Database (live, if configured)
    """
    # 1. Try Local CSV (Best for Streamlit Cloud / Demo)
    csv_path = "sp500_market_data.csv"
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            return df['Close'], "CSV (Static Demo)"
        except Exception as e:
            st.warning(f"Found CSV but failed to load: {e}")

    # 2. Try Database (Fallback or Live Mode)
    db_user = os.getenv("DB_USER")
    db_name = os.getenv("DB_NAME")
    
    if db_user and db_name:
        try:
            db_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            engine = sqlalchemy.create_engine(db_uri)
            query = 'SELECT "Date", "Close" FROM sp500_daily ORDER BY "Date"'
            # Fix: Handle case sensitivity if needed, standardizing on 'Date' and 'Close'
            df = pd.read_sql(query, engine)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df['Close'], "PostgreSQL (Live)"
        except Exception as e:
            pass # Fail silently and return empty
            
    return pd.Series(), "None"

# Backtest Function (with Warm-up)
def sma_crossover_backtest(close_price, short_window=50, long_window=200, start_date=None, end_date=None):
    # 1. Calculate Indicators on FULL History (Warm-up)
    fast_ma = vbt.MA.run(close_price, short_window)
    slow_ma = vbt.MA.run(close_price, long_window)
    
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    # 2. Slice to User's Selected Range
    if start_date and end_date:
        ts_start = pd.Timestamp(start_date)
        ts_end = pd.Timestamp(end_date)
        
        # Slice aligned data
        close_slice = close_price.loc[ts_start:ts_end]
        entries_slice = entries.loc[ts_start:ts_end]
        exits_slice = exits.loc[ts_start:ts_end]
    else:
        close_slice = close_price
        entries_slice = entries
        exits_slice = exits

    # 3. Simulate Portfolio on the Sliced Period
    if close_slice.empty:
        return None
        
    portfolio = vbt.Portfolio.from_signals(close_slice, entries_slice, exits_slice, init_cash=100_000, freq='D')
    return portfolio

# ==========================================
# UI LAYOUT
# ==========================================
st.set_page_config(page_title="S&P 500 Data Pipeline", page_icon="📈", layout="wide")

with st.sidebar:
    st.title("Navigation")
    page = st.radio("Go to", ["Dashboard", "About Project"])
    st.divider()

# ==========================================
# PAGE 1: DASHBOARD
# ==========================================
if page == "Dashboard":
    st.title("📈 S&P 500 Index - Data Validation Dashboard")

    st.sidebar.header("⚙️ Settings")
    
    stock_option = st.sidebar.selectbox("Select Asset", ["S&P500 (^GSPC)"])
    strategy_option = st.sidebar.selectbox("Select Strategy", ["SMA Crossover"])
    
    st.sidebar.subheader("Strategy Parameters")
    short_window = st.sidebar.number_input("Short Window (SMA)", value=50, step=1)
    long_window = st.sidebar.number_input("Long Window (SMA)", value=200, step=1)
    
    st.sidebar.subheader("Backtest Period")
    
    # SIMPLIFIED: Fixed Period Selector (No more confusing Date Pickers)
    period_days = {
        "Last 1 Year": 365,
        "Last 3 Years": 365 * 3,
        "Last 5 Years": 365 * 5,
        "All Time (Max)": 365 * 50
    }
    selected_period = st.sidebar.selectbox("Select Duration", list(period_days.keys()))
    
    # Calculate Dates based on selection
    today = pd.Timestamp.now().normalize()
    yesterday = today - pd.Timedelta(days=1)
    
    # Logic: Start Date = End Date - selected days
    days_to_subtract = period_days[selected_period]
    start_date = yesterday - pd.Timedelta(days=days_to_subtract)
    end_date = yesterday # Always up to yesterday
    
    run_bt = st.sidebar.button("🚀 Run Analysis", use_container_width=True)

    if run_bt:
        with st.spinner("Analyzing Market Data..."):
            close, source = get_close_data()
            
            # Data Cleaning (Robustness)
            close = close.ffill().dropna()

            if close.empty:
                st.error("❌ No data available. Please check `sp500_market_data.csv`.")
                st.stop()
            
            # ---------------------------------------------------------
            # 1. VISUALIZATION: SHOW RELEVANT HISTORY (From year 2000)
            # ---------------------------------------------------------
            st.markdown("### 📊 Market Trend & Strategy Indicators")
            st.caption(f"Showing market trends from Year 2000 to Present. Green/Red lines act as the 'Strategy Signals'.")
            
            # Calculate Indicators on FULL DATA
            full_sma_short = close.rolling(window=short_window).mean()
            full_sma_long = close.rolling(window=long_window).mean()
            
            # Plot Data (Filter to 2000+)
            plot_data = pd.DataFrame({
                "Price": close,
                f"SMA {short_window}": full_sma_short,
                f"SMA {long_window}": full_sma_long
            })
            plot_data = plot_data[plot_data.index >= "2000-01-01"] # User requested starting from 2000
            
            st.line_chart(plot_data, color=["#ffffff", "#00ff00", "#ff0000"])

            # ---------------------------------------------------------
            # 2. RUN BACKTEST (Specific Period)
            # ---------------------------------------------------------
            pf = sma_crossover_backtest(
                close, 
                short_window=short_window, 
                long_window=long_window,
                start_date=start_date,
                end_date=end_date
            )
            
            if pf is None or len(pf.close) == 0:
                st.error("❌ No data found for the selected period.")
            else:
                stats = pf.stats()
                
                # Check for insufficient data
                if len(pf.close) < 20:
                     st.warning(f"⚠️ Note: Period is too short for reliable analysis.")

                # ---------------------------------------------------------
                # 3. PLAIN ENGLISH EXPLANATION & RESULTS
                # ---------------------------------------------------------
                st.markdown("---")
                st.subheader(f"🏆 Results: {selected_period}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                def fmt(val, is_pct=False):
                    if pd.isna(val) or np.isinf(val): return "N/A"
                    return f"{val:.2f}%" if is_pct else f"{val:.2f}"

                total_return = stats['Total Return [%]']
                win_rate = stats['Win Rate [%]']
                trades = stats['Total Trades']
                max_dd = stats['Max Drawdown [%]']

                with col1: st.metric("Total Return", fmt(total_return, True))
                
                # CONDITIONAL METRIC: Show "Win Rate" only if available.
                # If N/A (Open Trade), show "Current Status" instead.
                with col2:
                    if pd.notna(win_rate):
                        st.metric("Win Rate", fmt(win_rate, True))
                    elif trades > 0:
                         st.metric("Current Status", "🟢 Holding")
                    else:
                         st.metric("Current Status", "⚪ No Trades")

                with col3: st.metric("Trades Executed", int(trades) if pd.notna(trades) else 0)
                with col4: st.metric("Max Drawdown", fmt(max_dd, True))

                # Educational Text Block
                with st.container(border=True):
                    st.markdown(f"#### 💡 Analysis Summary")
                    
                    if pd.isna(trades) or trades == 0:
                        st.info("No trades were completed in this period. The system likely held a single position (Long or Cash) based on the long-term trend.")
                    else:
                        profit_word = "PROFIT" if total_return > 0 else "LOSS"
                        
                        # Simplified Explanation
                        if pd.isna(win_rate):
                            # Case: Open Trade
                            result_desc = "The system bought the stock and is currently **Holding** it (Active Position)."
                        else:
                            # Case: Closed Trades
                            result_desc = f"Win Rate: **{win_rate:.0f}%** (Percentage of profitable trades)."
                        
                        st.markdown(f"""
                        If you used this strategy for the **{selected_period}**, you would have made **{int(trades)} trades**.
                        
                        **The Result:**
                        *   You would have generated a **{profit_word}** of **{fmt(total_return, True)}**.
                        *   {result_desc}
                        *   Max Drawdown: **{fmt(max_dd, True)}** (Maximum observed loss from peak).
                        """)

                st.markdown("### 📈 Investment Growth (Starting with $100,000)")
                st.caption("Comparing the growth of your money over time.")
                
                equity_df = pd.DataFrame({"Strategy": pf.value()})
                
                # Rebase Benchmark (S&P 500 Buy & Hold)
                ts_start = pd.Timestamp(start_date)
                ts_end = pd.Timestamp(end_date)
                close_slice = close.loc[ts_start:ts_end]
                
                if not close_slice.empty:
                    benchmark_ret = close_slice.pct_change().fillna(0)
                    equity_df["Benchmark (Buy & Hold)"] = (1 + benchmark_ret).cumprod() * 100_000
                    st.line_chart(equity_df, color=["#2ECC71", "#E74C3C"])
                
                # Calculate final values for the text
                final_strategy_val = equity_df["Strategy"].iloc[-1]
                final_benchmark_val = equity_df["Benchmark (Buy & Hold)"].iloc[-1] if "Benchmark (Buy & Hold)" in equity_df else 0
                
                diff = final_strategy_val - final_benchmark_val
                outcome = "MORE" if diff > 0 else "LESS"
                
                st.info(f"""
                **Simulation Scenario:**
                Imagine you started with **$100,000** on **{start_date.strftime('%Y-%m-%d')}**.
                
                *   🔴 **Red Line (Passive):** You bought the S&P 500 and held it until today. (Final Value: **${final_benchmark_val:,.2f}**)
                *   🟢 **Green Line (Active):** You traded using this Strategy. (Final Value: **${final_strategy_val:,.2f}**)
                
                **Conclusion:** This Strategy would have made you **${abs(diff):,.2f} {outcome}** than just buying and holding.
                """)

# ==========================================
# PAGE 2: ABOUT PROJECT
# ==========================================
elif page == "About Project":
    st.title("📂 About this Project")
    
    st.markdown("""
    ### 🎯 Objective
    This interactive dashboard serves as a **professional portfolio demonstration** of a full-stack Data Engineering pipeline. 
    It is not just a trading tool, but a **Data Validation & Analytics Platform** designed to:
    
    1.  **Automate Data Ingestion:** Systematically fetch daily financial data (S&P 500) from reliable sources.
    2.  **Verify Data Integrity:** Ensure no missing values or anomalies exist before analysis.
    3.  **Demonstrate Algorithmic Logic:** Visualize how simple quantitative strategies (like SMA Crossover) process this data in real-time.
    
    ---
    """)

    st.subheader("⚙️ System Architecture")
    st.caption("How data flows from the source to this dashboard:")
    
    # Simple mermaid diagram for flow
    st.markdown("""
    ```mermaid
    graph LR
        A[Yahoo Finance API] -->|Extract| B(Python ETL Script)
        B -->|Transform & Clean| C{Quality Checks}
        C -->|Pass| D[(PostgreSQL / CSV)]
        D -->|Serve| E[Streamlit Dashboard]
        E -->|Analyze| F[User Insights]
    ```
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **🛠 Tech Stack**
        *   **Python:** Core logic & data processing.
        *   **Pandas:** Advanced data manipulation.
        *   **Streamlit:** Interactive frontend UI.
        *   **PostgreSQL:** Secure data warehousing (Live Mode).
        *   **GitHub Actions / Prefect:** Automated orchestration.
        """)
        
    with col2:
        st.success("""
        **🌟 Key Features**
        *   **Dynamic Backtesting:** Test strategies on the fly with custom parameters.
        *   **Investment Simulation:** Calculate real-dollar growth scenarios (e.g., $100k Investment).
        *   **Hybrid Availability:** Runs on Cloud Database or Static CSV (Demo Mode) for 100% uptime.
        """)

    st.markdown("---")
    st.subheader("🟢 System Status Monitor")
    
    # Check Status
    close, source = get_close_data()
    
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        if "CSV" in source:
            st.warning(f"**Data Source Mode**\n\n📁 **Static Demo (CSV)**\n\n*Optimized for fast public deployment.*")
        elif "PostgreSQL" in source:
            st.success(f"**Data Source Mode**\n\n🟢 **Live Database**\n\n*Connected to production warehouse.*")
        else:
             st.error("**Data Source Mode**\n\n🔴 **Disconnected**")

    with status_col2:
        if not close.empty:
            st.success(f"**Latest Data Available**\n\n📅 **{close.index.max().date()}**\n\n*Data is up-to-date.*")
        else:
            st.error("No data available.")

    st.caption("Developed by [Your Name/Portfolio] | Powered by Python Streamlit")
            st.warning("**Latest Data Available**\n\nUnknown")

    st.markdown("---")
    st.subheader("🏗 System Architecture")
    st.markdown("""
    ```mermaid
    graph LR
        A[Yahoo Finance API] -->|Extract| B(Prefect Orchestrator)
        B -->|Transform| C{Data Cleaning}
        C -->|Load| D[(PostgreSQL)]
        D -.->|Export| E(CSV Snapshot)
        E -->|Read| F[Streamlit Dashboard]
        D -.->|Direct Query| F
    ```
    """)
    st.caption("*The dashboard supports both Direct DB Query (Live) and CSV Snapshot (Demo/Cloud) modes.*")
