from prefect.deployments import Deployment
from prefect.orion.schemas.schedules import IntervalSchedule
from datetime import timedelta, datetime
from sp500_pipeline import run_pipeline

# schedule ทุกวัน เริ่มจากวันที่ 29 กันยายน 2025 เวลา 08:00
daily_schedule = IntervalSchedule(
    interval=timedelta(days=1),
    anchor_date=datetime(2025, 9, 29, 8, 0)
)

deployment = Deployment.build_from_flow(
    flow=run_pipeline,
    name="daily-sp500-pipeline",
    schedule=daily_schedule
)

if __name__ == "__main__":
    deployment.apply()  