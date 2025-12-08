"""
sp500_pipeline.py
=================

Pipeline สำหรับดึงข้อมูลหุ้น S&P500 จาก Yahoo Finance,
ทำความสะอาดข้อมูล,
คำนวณค่า Moving Average (MA),
บันทึกข้อมูลลงฐานข้อมูล PostgreSQL,
และ export ข้อมูล 100 แถวล่าสุดเป็นไฟล์ CSV

การใช้งาน:
1. ตรวจสอบไฟล์ .env ให้ครบ (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
2. รัน: python sp500_pipeline.py

Tasks:
- Task 1: fetch_sp500_data()      → ดึงข้อมูลจาก Yahoo Finance
- Task 2: clean_data()             → ทำความสะอาดข้อมูลก่อนวิเคราะห์
- Task 3: calculate_moving_averages() → คำนวณค่า MA
- Task 4: save_to_postgres()       → บันทึกข้อมูลลง PostgreSQL
- Task 5: export_latest_data()     → export ข้อมูลล่าสุด 100 แถวเป็น CSV
"""

import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from prefect import task, flow
from datetime import datetime
import os
from dotenv import load_dotenv

# โหลด Environment Variables
load_dotenv()

# ===========================
# Task 1: Fetch ข้อมูล S&P500
# ===========================
@task
def fetch_sp500_data(period: str = "max", interval: str = "1d") -> pd.DataFrame:
    """
    ดึงข้อมูลราคาหุ้น S&P500 จาก Yahoo Finance

    Args:
        period (str): ช่วงข้อมูลที่ต้องการ ('max', '1y', '3mo' เป็นต้น)
        interval (str): ความถี่ของข้อมูล ('1d' สำหรับรายวัน)

    Returns:
        pd.DataFrame: ข้อมูลราคาหุ้น พร้อมคอลัมน์ date, Open, High, Low, Close, Volume
    """
    ticker = "^GSPC"
    df = yf.download(ticker, period=period, interval=interval)

    # Flatten MultiIndex columns ถ้ามี
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    if df.empty:
        raise ValueError("ไม่พบข้อมูลจาก Yahoo Finance")

    df.reset_index(inplace=True)
    df.rename(columns={"Date": "date"}, inplace=True)

    print(f"[Fetch] ข้อมูลล่าสุด: {df['date'].max()}")
    return df

# ===========================
# Task 2: Clean ข้อมูลก่อนวิเคราะห์
# ===========================
@task
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    ทำความสะอาดข้อมูลก่อนนำไปวิเคราะห์หรือบันทึกลงฐานข้อมูล

    Steps:
    1. ลบค่า NaN ในคอลัมน์สำคัญที่มีอยู่จริง
    2. แปลง date column เป็น datetime
    3. ลบข้อมูลซ้ำตามวันที่
    4. เรียงลำดับข้อมูลตามวันที่
    5. กรองข้อมูลราคาหรือปริมาณติดลบ
    """
    # กำหนดคอลัมน์สำคัญ
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    # เลือกเฉพาะคอลัมน์ที่มีอยู่จริง
    existing_cols = [col for col in required_cols if col in df.columns]

    # ลบค่า NaN
    df = df.dropna(subset=existing_cols)

    # แปลง date เป็น datetime
    df["date"] = pd.to_datetime(df["date"])

    # ลบข้อมูลซ้ำตามวันที่
    df = df.drop_duplicates(subset=["date"], keep="last")

    # เรียงลำดับ
    df = df.sort_values(by="date").reset_index(drop=True)

    # กรองข้อมูลติดลบ
    for col in existing_cols:
        df = df[df[col] >= 0]

    print(f"[Clean] หลังทำความสะอาดเหลือ {len(df)} แถว")
    return df

# ===========================
# Task 3: คำนวณ Moving Average
# ===========================
@task
def calculate_moving_averages(df: pd.DataFrame, windows=[20, 50, 100, 200]) -> pd.DataFrame:
    """
    คำนวณค่า Moving Average (MA) ของราคาปิด

    Args:
        df (pd.DataFrame): DataFrame ข้อมูลหุ้น
        windows (list): รายการช่วงเวลาที่ต้องการคำนวณ MA

    Returns:
        pd.DataFrame: เพิ่มคอลัมน์ MA_20, MA_50, MA_100, MA_200
    """
    for w in windows:
        if "Close" in df.columns:
            df[f"MA_{w}"] = df["Close"].rolling(window=w).mean()

    print(f"[MA] ตัวอย่างข้อมูล:\n{df.tail(3)}")
    return df

# ===========================
# Task 4: Save ลง PostgreSQL
# ===========================
@task
def save_to_postgres(df: pd.DataFrame, table_name="sp500_prices"):
    """
    บันทึกข้อมูลลง PostgreSQL
    - สร้าง table ถ้าไม่เคยมี
    - append เฉพาะข้อมูลใหม่
    """
    db_uri = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    engine = create_engine(db_uri)

    last_date = None
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT MAX(date) FROM {table_name}"))
            last_date = result.scalar()
    except Exception as e:
        if "relation" in str(e) and "does not exist" in str(e):
            print(f"[DB] ตาราง '{table_name}' ยังไม่มีอยู่ จะสร้างใหม่ทั้งหมด")
        else:
            raise e

    if last_date:
        df_new = df[df["date"] > pd.to_datetime(last_date)]
    else:
        df_new = df

    if not df_new.empty:
        df_new.to_sql(table_name, con=engine, if_exists="append", index=False)
        print(f"[DB] บันทึกข้อมูลใหม่ {len(df_new)} แถว")
    else:
        print("[DB] ไม่มีข้อมูลใหม่ให้บันทึก")

# ===========================
# Task 5: Export ข้อมูลล่าสุด 100 แถว
# ===========================
@task
def export_latest_data(table_name="sp500_prices", output_file="sp500_latest.csv", limit=100):
    """
    ดึงข้อมูลล่าสุดจาก PostgreSQL และ export เป็นไฟล์ CSV
    """
    db_uri = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    engine = create_engine(db_uri)

    query = f"""
        SELECT * FROM {table_name}
        ORDER BY date DESC
        LIMIT {limit};
    """
    df = pd.read_sql(query, con=engine)
    df.to_csv(output_file, index=False)
    print(f"[Export] บันทึกไฟล์ล่าสุด {limit} แถว -> {output_file}")
    return output_file

# ===========================
# Main Flow
# ===========================
@flow(name="SP500_Daily_Pipeline")
def run_pipeline():
    """
    Main pipeline flow
    """
    print(f"เริ่ม Pipeline วันที่ {datetime.now()}")

    # Task 1: ดึงข้อมูล
    df = fetch_sp500_data()

    # Task 2: ทำความสะอาด
    df = clean_data(df)

    # Task 3: คำนวณ MA
    df = calculate_moving_averages(df)

    # Task 4: บันทึกลง DB
    save_to_postgres(df)

    # Task 5: Export ข้อมูลล่าสุด
    export_latest_data()

    print("✅ เสร็จสิ้น Pipeline ทั้งหมด!")

# ===========================
# Run
# ===========================
if __name__ == "__main__":
    run_pipeline()


