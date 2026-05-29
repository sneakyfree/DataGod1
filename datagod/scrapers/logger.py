import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from datagod.config.settings import DATABASE_URL

logger = logging.getLogger(__name__)


class ScraperLogger:
    """
    Handles structured logging of scraper runs to the database.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        if not self.db_session:
            # Fallback to creating a new session if one isn't provided
            # This is useful for standalone scripts
            try:
                engine = create_engine(DATABASE_URL)
                self.db_session = Session(bind=engine)
            except Exception as e:
                logger.error(
                    f"Failed to initialize DB connection for ScraperLogger: {e}"
                )

    def log_run_start(
        self,
        scraper_name: str,
        jurisdiction_id: Optional[int] = None,
        data_category: str = "general",
    ) -> int:
        """
        Log the start of a scraper run.
        Returns the run_id.
        """
        if not self.db_session:
            logger.warning("No DB session available, skipping log_run_start")
            return 0

        try:
            # Using raw SQL to avoid circular imports or model dependency issues for now
            # In a full ORM setup, we would use the ScraperRun model
            query = text(
                """
                INSERT INTO scraper_runs 
                (scraper_module, jurisdiction_id, data_category, started_at, status)
                VALUES (:scraper_name, :jurisdiction_id, :data_category, :started_at, 'running')
                RETURNING id
            """
            )

            result = self.db_session.execute(
                query,
                {
                    "scraper_name": scraper_name,
                    "jurisdiction_id": jurisdiction_id,
                    "data_category": data_category,
                    "started_at": datetime.utcnow(),
                },
            )
            self.db_session.commit()
            run_id = result.scalar()
            return run_id
        except Exception as e:
            logger.error(f"Failed to log run start: {e}")
            self.db_session.rollback()
            return 0

    def log_run_end(
        self,
        run_id: int,
        status: str,
        items_scraped: int = 0,
        error_message: Optional[str] = None,
    ):
        """
        Log the completion (success or failure) of a scraper run.
        """
        if not self.db_session or not run_id:
            return

        try:
            query = text(
                """
                UPDATE scraper_runs
                SET completed_at = :completed_at,
                    status = :status,
                    records_found = :records_found,
                    error_message = :error_message
                WHERE id = :run_id
            """
            )

            self.db_session.execute(
                query,
                {
                    "completed_at": datetime.utcnow(),
                    "status": status,
                    "records_found": items_scraped,
                    "error_message": error_message,
                    "run_id": run_id,
                },
            )
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Failed to log run end: {e}")
            self.db_session.rollback()

    def update_metrics(self, run_id: int, metrics: Dict[str, Any]):
        """
        Update the run with detailed metrics (stored as JSON if column exists).
        Note: The 005 migration didn't explicitly add a metrics JSON column,
        but we can try to store it in notes or if we modify schema later.
        For now, we'll just log it.
        """
        logger.info(f"Run {run_id} metrics: {metrics}")
