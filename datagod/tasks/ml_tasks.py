"""
DataGod ML Tasks
Celery tasks for anomaly detection, data quality checks, and ML pipelines
"""

import logging
from typing import List, Optional

from datagod.tasks import celery_app

logger = logging.getLogger("datagod.tasks.ml")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def run_anomaly_detection(
    self, record_ids: Optional[List[int]] = None, detection_method: str = "statistical"
):
    """
    Run anomaly detection on specified records or all recent records.

    Args:
        record_ids: Optional list of record IDs to analyze; if None, analyzes recent
        detection_method: Detection method to use (statistical, isolation_forest, rule_based)
    """
    try:
        logger.info(
            f"Starting anomaly detection: method={detection_method}, records={len(record_ids) if record_ids else 'all'}"
        )

        from datagod.ml.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()
        results = detector.detect(record_ids=record_ids, method=detection_method)

        anomaly_count = (
            len([r for r in results if r.get("is_anomaly", False)]) if results else 0
        )

        logger.info(
            f"Anomaly detection completed: {anomaly_count} anomalies found in {len(results) if results else 0} records"
        )

        return {
            "status": "completed",
            "detection_method": detection_method,
            "records_analyzed": len(results) if results else 0,
            "anomalies_found": anomaly_count,
        }

    except Exception as exc:
        logger.error(f"Anomaly detection failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task
def run_anomaly_scan():
    """Periodic task: scan recent records for anomalies."""
    logger.info("Running periodic anomaly scan")
    return run_anomaly_detection.delay(detection_method="statistical")


@celery_app.task
def check_data_quality():
    """
    Periodic task: run data quality checks across all records and sources.
    Returns quality metrics for the data quality dashboard.
    """
    try:
        logger.info("Running periodic data quality check")

        from datagod.db_manager import get_session

        session = get_session()
        try:
            # Count total records
            total_records = (
                session.execute("SELECT COUNT(*) FROM records").scalar() or 0
            )
            # Count records with missing fields
            missing_title = (
                session.execute(
                    "SELECT COUNT(*) FROM records WHERE title IS NULL OR title = ''"
                ).scalar()
                or 0
            )
            missing_date = (
                session.execute(
                    "SELECT COUNT(*) FROM records WHERE date IS NULL"
                ).scalar()
                or 0
            )
            missing_amount = (
                session.execute(
                    "SELECT COUNT(*) FROM records WHERE amount IS NULL"
                ).scalar()
                or 0
            )

            completeness = (
                1.0
                - (
                    (missing_title + missing_date + missing_amount)
                    / (total_records * 3)
                )
                if total_records > 0
                else 0
            )

            result = {
                "status": "completed",
                "total_records": total_records,
                "completeness_score": round(completeness * 100, 1),
                "missing_fields": {
                    "title": missing_title,
                    "date": missing_date,
                    "amount": missing_amount,
                },
            }

            logger.info(
                f"Data quality check completed: completeness={result['completeness_score']}%"
            )
            return result
        finally:
            session.close()

    except Exception as exc:
        logger.error(f"Data quality check failed: {exc}", exc_info=True)
        return {"status": "error", "error": str(exc)}
