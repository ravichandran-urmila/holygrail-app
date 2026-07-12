from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from . import screener
from .indicator import HGSettings

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_screener_job(universe: str):
    log.info(f"Starting cron job for universe: {universe}")
    settings = HGSettings()
    screener.start(settings, universe, force=True)

def start_scheduler():
    if not scheduler.running:
        # Schedule S&P 500 at 2 AM EST (which is roughly UTC-5)
        # Using timezone 'America/New_York'
        scheduler.add_job(
            run_screener_job,
            CronTrigger(day_of_week='sat', hour=2, minute=0, timezone='America/New_York'),
            args=['sp500'],
            id='sp500_cron',
            replace_existing=True
        )
        
        # Schedule Russell 1000 at 4 AM EST
        scheduler.add_job(
            run_screener_job,
            CronTrigger(day_of_week='sat', hour=4, minute=0, timezone='America/New_York'),
            args=['russell1000'],
            id='russell1000_cron',
            replace_existing=True
        )
        
        # Schedule Russell 2000 at 6 AM EST
        scheduler.add_job(
            run_screener_job,
            CronTrigger(day_of_week='sat', hour=6, minute=0, timezone='America/New_York'),
            args=['russell2000'],
            id='russell2000_cron',
            replace_existing=True
        )

        scheduler.start()
        log.info("APScheduler started.")
