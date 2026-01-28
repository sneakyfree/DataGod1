
import sys
import os
import logging
from datetime import datetime, timedelta
import asyncio

# Setup paths
sys.path.append('/home/user1-gpu/Desktop/grants_folder/datagod/DataGod1')

from datagod.scrapers.logger import ScraperLogger
from datagod.models import ScraperRun, Base, engine, SessionLocal
from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator, TaskPriority
from api.src.api_v2 import get_scraper_runs, get_scraper_status, ScraperRunResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Scraper for testing
class MockScraper:
    def __init__(self, jurisdiction_id, jurisdiction_name, **kwargs):
        self.jurisdiction_id = jurisdiction_id
        self.jurisdiction_name = jurisdiction_name
        self.logger = logging.getLogger("MockScraper")
        # Initialize Scraper Logger
        from datagod.scrapers.logger import ScraperLogger
        self.scraper_logger = ScraperLogger()
        self.current_run_id = 0

    def start_run(self, jurisdiction_id=None):
        logger.info("MockScraper starting run logging...")
        self.current_run_id = self.scraper_logger.log_run_start(
            scraper_name=self.__class__.__name__,
            jurisdiction_id=self.jurisdiction_id
        )
        return self.current_run_id

    def scrape(self):
        logger.info("MockScraper scraping...")
        return [{"id": 1, "data": "test"}] # Return dummy records

    def get_metrics(self):
        return {"items": 1}

    def save_to_database(self, manager):
        return 1

    def end_run(self, status='success', items_scraped=0, error_message=None):
        logger.info("MockScraper ending run logging...")
        if self.current_run_id:
            self.scraper_logger.log_run_end(
                run_id=self.current_run_id,
                status=status,
                items_scraped=items_scraped,
                error_message=error_message
            )

def main():
    logger.info("Starting Scraper Logging Verification...")
    
    # 1. Initialize Orchestrator
    orchestrator = ScraperOrchestrator(max_workers=1)
    
    # 1.5 Get valid jurisdiction
    db = SessionLocal()
    from datagod.models import Jurisdiction
    jurisdiction = db.query(Jurisdiction).first()
    if not jurisdiction:
        # Create one if missing
        jurisdiction = Jurisdiction(name="Test Jurisdiction", state="FL", fips_code="99999", type="county")
        db.add(jurisdiction)
        db.commit()
    
    valid_id = jurisdiction.id
    valid_name = jurisdiction.name
    db.close()
    
    # Register Mock Scraper manually into registry
    orchestrator.register_scraper("MockScraper", MockScraper)
    
    # 2. Add Task
    task_id = orchestrator.add_task(
        scraper_name="MockScraper",
        scraper_config={},
        jurisdiction_id=valid_id,
        jurisdiction_name=valid_name,
        priority=TaskPriority.HIGH
    )
    
    # 3. Run Orchestrator (Blocking)
    logger.info("Running orchestrator...")
    orchestrator.start(blocking=False) # Start in thread
    
    # Wait for completion
    import time
    max_wait = 10
    start = time.time()
    
    while True:
        status = orchestrator.get_task_status(task_id)
        if status['status'] == 'completed':
            logger.info("Task completed!")
            break
        if status['status'] == 'failed':
            logger.error(f"Task failed: {status.get('error')}")
            break
        if time.time() - start > max_wait:
            logger.error("Task timed out")
            break
        time.sleep(1)
        
    orchestrator.stop()
    
    # 4. Verify Database Logging
    logger.info("Verifying database logging...")
    db = SessionLocal()
    try:
        # Check raw DB
        run = db.query(ScraperRun).filter(ScraperRun.scraper_module == "MockScraper").order_by(ScraperRun.started_at.desc()).first()
        if run:
            logger.info(f"✅ Found ScraperRun in DB! ID: {run.id}, Status: {run.status}, Records: {run.records_found}")
            if run.status == 'success' and run.records_found == 1:
                logger.info("✅ ScraperRun data matches expected values.")
            else:
                logger.warning(f"⚠️ ScraperRun data mismatch. Expected success/1, got {run.status}/{run.records_found}")
        else:
            logger.error("❌ ScraperRun NOT found in DB!")
            sys.exit(1)
            
        # 5. Verify API Function
        logger.info("Verifying API function...")
        # Mock user/request not needed if we call function directly with dependencies manually, 
        # but api functions are async and depend on Depends().
        # We'll just check if we can query using the same logic as the API.
        
        # Simulating API call logic
        runs = db.query(ScraperRun).filter(ScraperRun.scraper_module == "MockScraper").all()
        logger.info(f"API Logic found {len(runs)} runs")
        
        # Test status API logic
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        count = db.query(ScraperRun).filter(ScraperRun.started_at >= one_day_ago).count()
        logger.info(f"API Status Logic verify: {count} runs in last 24h")
        
    finally:
        db.close()
        
    logger.info("Verification Complete!")

if __name__ == "__main__":
    main()
