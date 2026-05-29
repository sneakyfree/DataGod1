"""
DataGod Scraper Tasks
Celery tasks for running scrapers asynchronously
"""

import logging
from typing import Optional

from datagod.tasks import celery_app

logger = logging.getLogger("datagod.tasks.scraper")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def run_scraper(self, jurisdiction_id: int, scraper_type: str = "business_filings"):
    """
    Run a scraper for a specific jurisdiction asynchronously.

    Args:
        jurisdiction_id: ID of the jurisdiction to scrape
        scraper_type: Type of scraper to run
    """
    try:
        logger.info(
            f"Starting scraper task: jurisdiction={jurisdiction_id}, type={scraper_type}"
        )

        from datagod.db_manager import get_session
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        session = get_session()

        try:
            jurisdiction = session.execute(
                "SELECT * FROM jurisdictions WHERE id = :id", {"id": jurisdiction_id}
            ).fetchone()

            if not jurisdiction:
                logger.error(f"Jurisdiction {jurisdiction_id} not found")
                return {"status": "error", "message": "Jurisdiction not found"}

            results = orchestrator.scrape_jurisdiction(jurisdiction)

            logger.info(
                f"Scraper completed: jurisdiction={jurisdiction_id}, "
                f"records_found={len(results) if results else 0}"
            )

            return {
                "status": "completed",
                "jurisdiction_id": jurisdiction_id,
                "records_found": len(results) if results else 0,
            }
        finally:
            session.close()

    except Exception as exc:
        logger.error(f"Scraper task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=600)
def run_bulk_scrape(self, state_code: str):
    """
    Run scrapers for all jurisdictions in a state.

    Args:
        state_code: Two-letter state code
    """
    try:
        logger.info(f"Starting bulk scrape for state: {state_code}")

        from datagod.db_manager import get_session

        session = get_session()
        try:
            jurisdictions = session.execute(
                "SELECT id FROM jurisdictions WHERE state = :state",
                {"state": state_code},
            ).fetchall()

            task_ids = []
            for j in jurisdictions:
                task = run_scraper.delay(j.id)
                task_ids.append(task.id)

            logger.info(f"Dispatched {len(task_ids)} scraper tasks for {state_code}")

            return {
                "status": "dispatched",
                "state": state_code,
                "task_count": len(task_ids),
                "task_ids": task_ids,
            }
        finally:
            session.close()

    except Exception as exc:
        logger.error(f"Bulk scrape task failed for {state_code}: {exc}")
        raise self.retry(exc=exc)
