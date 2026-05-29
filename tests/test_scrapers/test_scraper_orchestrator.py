"""
Tests for datagod/scrapers/scraper_orchestrator.py

Comprehensive tests for the Scraper Orchestration System.
"""

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestTaskStatusEnum:
    """Tests for TaskStatus enum"""

    def test_task_status_exists(self):
        """Test that TaskStatus enum exists"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus is not None

    def test_task_status_has_pending(self):
        """Test that TaskStatus has PENDING"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "PENDING")

    def test_task_status_has_queued(self):
        """Test that TaskStatus has QUEUED"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "QUEUED")

    def test_task_status_has_running(self):
        """Test that TaskStatus has RUNNING"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "RUNNING")

    def test_task_status_has_completed(self):
        """Test that TaskStatus has COMPLETED"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "COMPLETED")

    def test_task_status_has_failed(self):
        """Test that TaskStatus has FAILED"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "FAILED")

    def test_task_status_has_cancelled(self):
        """Test that TaskStatus has CANCELLED"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "CANCELLED")

    def test_task_status_has_retry(self):
        """Test that TaskStatus has RETRY"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert hasattr(TaskStatus, "RETRY")


class TestTaskPriorityEnum:
    """Tests for TaskPriority enum"""

    def test_task_priority_exists(self):
        """Test that TaskPriority enum exists"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority is not None

    def test_task_priority_has_critical(self):
        """Test that TaskPriority has CRITICAL"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert hasattr(TaskPriority, "CRITICAL")
        assert TaskPriority.CRITICAL.value == 1

    def test_task_priority_has_high(self):
        """Test that TaskPriority has HIGH"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert hasattr(TaskPriority, "HIGH")
        assert TaskPriority.HIGH.value == 2

    def test_task_priority_has_normal(self):
        """Test that TaskPriority has NORMAL"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert hasattr(TaskPriority, "NORMAL")
        assert TaskPriority.NORMAL.value == 3

    def test_task_priority_has_low(self):
        """Test that TaskPriority has LOW"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert hasattr(TaskPriority, "LOW")
        assert TaskPriority.LOW.value == 4

    def test_task_priority_has_background(self):
        """Test that TaskPriority has BACKGROUND"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert hasattr(TaskPriority, "BACKGROUND")
        assert TaskPriority.BACKGROUND.value == 5


class TestScrapingTask:
    """Tests for ScrapingTask dataclass"""

    def test_scraping_task_exists(self):
        """Test that ScrapingTask class exists"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask

        assert ScrapingTask is not None

    def test_scraping_task_has_required_fields(self):
        """Test that ScrapingTask has required fields"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask

        # Check annotations for fields
        assert "priority" in ScrapingTask.__dataclass_fields__
        assert "task_id" in ScrapingTask.__dataclass_fields__
        assert "scraper_class" in ScrapingTask.__dataclass_fields__
        assert "scraper_config" in ScrapingTask.__dataclass_fields__
        assert "jurisdiction_id" in ScrapingTask.__dataclass_fields__
        assert "jurisdiction_name" in ScrapingTask.__dataclass_fields__
        assert "status" in ScrapingTask.__dataclass_fields__

    def test_scraping_task_create_method(self):
        """Test that ScrapingTask.create() factory method works"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskPriority

        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={"key": "value"},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            priority=TaskPriority.NORMAL,
        )

        assert task.scraper_class == "TestScraper"
        assert task.jurisdiction_id == 1
        assert task.jurisdiction_name == "Test County"
        assert task.priority == TaskPriority.NORMAL.value
        assert task.task_id is not None

    def test_scraping_task_to_dict(self):
        """Test that ScrapingTask.to_dict() works"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskPriority

        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        result = task.to_dict()
        assert isinstance(result, dict)
        assert "task_id" in result
        assert "scraper_class" in result
        assert "jurisdiction_id" in result
        assert "status" in result


class TestWorkerStats:
    """Tests for WorkerStats dataclass"""

    def test_worker_stats_exists(self):
        """Test that WorkerStats class exists"""
        from datagod.scrapers.scraper_orchestrator import WorkerStats

        assert WorkerStats is not None

    def test_worker_stats_has_fields(self):
        """Test that WorkerStats has required fields"""
        from datagod.scrapers.scraper_orchestrator import WorkerStats

        stats = WorkerStats(worker_id="worker-1")
        assert stats.worker_id == "worker-1"
        assert stats.tasks_completed == 0
        assert stats.tasks_failed == 0
        assert stats.total_records == 0
        assert stats.is_active is True


class TestTaskQueue:
    """Tests for TaskQueue class"""

    def test_task_queue_exists(self):
        """Test that TaskQueue class exists"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        assert TaskQueue is not None

    def test_task_queue_init(self):
        """Test TaskQueue initialization"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        queue = TaskQueue()
        assert queue.size() == 0

    def test_task_queue_put_and_get(self):
        """Test TaskQueue put and get"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskQueue

        queue = TaskQueue()
        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        queue.put(task)
        assert queue.size() == 1

        retrieved = queue.get(timeout=0.1)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_task_queue_priority_ordering(self):
        """Test that TaskQueue respects priority"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()

        low_task = ScrapingTask.create(
            scraper_class="LowPriority",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Low",
            priority=TaskPriority.LOW,
        )

        high_task = ScrapingTask.create(
            scraper_class="HighPriority",
            scraper_config={},
            jurisdiction_id=2,
            jurisdiction_name="High",
            priority=TaskPriority.HIGH,
        )

        queue.put(low_task)
        queue.put(high_task)

        # High priority should come first
        first = queue.get(timeout=0.1)
        assert first.scraper_class == "HighPriority"

    def test_task_queue_peek(self):
        """Test TaskQueue peek method"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskQueue

        queue = TaskQueue()
        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        queue.put(task)

        peeked = queue.peek()
        assert peeked is not None
        assert queue.size() == 1  # Still in queue

    def test_task_queue_get_task_by_id(self):
        """Test TaskQueue get_task method"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskQueue

        queue = TaskQueue()
        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        queue.put(task)
        retrieved = queue.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_task_queue_get_all_tasks(self):
        """Test TaskQueue get_all_tasks method"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskQueue

        queue = TaskQueue()

        for i in range(3):
            task = ScrapingTask.create(
                scraper_class=f"Scraper{i}",
                scraper_config={},
                jurisdiction_id=i,
                jurisdiction_name=f"County{i}",
            )
            queue.put(task)

        all_tasks = queue.get_all_tasks()
        assert len(all_tasks) == 3


class TestScraperOrchestrator:
    """Tests for ScraperOrchestrator class"""

    def test_scraper_orchestrator_exists(self):
        """Test that ScraperOrchestrator class exists"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        assert ScraperOrchestrator is not None

    def test_scraper_orchestrator_init(self):
        """Test ScraperOrchestrator initialization"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator(max_workers=3)
        assert orchestrator.max_workers == 3
        assert orchestrator._running is False

    def test_register_scraper(self):
        """Test registering a scraper"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        mock_scraper_class = Mock

        orchestrator.register_scraper("test_scraper", mock_scraper_class)
        assert "test_scraper" in orchestrator._scraper_registry

    def test_add_task(self):
        """Test adding a task"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        orchestrator.register_scraper("test_scraper", Mock)

        task_id = orchestrator.add_task(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        assert task_id is not None
        assert orchestrator._metrics["total_tasks"] == 1

    def test_add_task_unknown_scraper_raises(self):
        """Test that adding task with unknown scraper raises error"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        with pytest.raises(ValueError):
            orchestrator.add_task(
                scraper_name="unknown_scraper",
                scraper_config={},
                jurisdiction_id=1,
                jurisdiction_name="Test County",
            )

    def test_add_bulk_tasks(self):
        """Test adding multiple tasks at once"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        orchestrator.register_scraper("test_scraper", Mock)

        tasks = [
            {
                "scraper_name": "test_scraper",
                "jurisdiction_id": i,
                "jurisdiction_name": f"County{i}",
            }
            for i in range(5)
        ]

        task_ids = orchestrator.add_bulk_tasks(tasks)
        assert len(task_ids) == 5
        assert orchestrator._metrics["total_tasks"] == 5

    def test_get_task_status(self):
        """Test getting task status"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        orchestrator.register_scraper("test_scraper", Mock)

        task_id = orchestrator.add_task(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        status = orchestrator.get_task_status(task_id)
        assert status is not None
        assert "task_id" in status
        assert "status" in status

    def test_get_queue_status(self):
        """Test getting queue status"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        orchestrator.register_scraper("test_scraper", Mock)

        orchestrator.add_task(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        status = orchestrator.get_queue_status()
        assert "queue_size" in status
        assert "total_tasks" in status
        assert "by_status" in status

    def test_get_worker_stats(self):
        """Test getting worker stats"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator(max_workers=3)
        orchestrator.start()
        time.sleep(0.1)

        stats = orchestrator.get_worker_stats()
        assert len(stats) == 3

        orchestrator.stop()

    def test_get_metrics(self):
        """Test getting orchestrator metrics"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()
        metrics = orchestrator.get_metrics()

        assert "total_tasks" in metrics
        assert "completed_tasks" in metrics
        assert "failed_tasks" in metrics
        assert "total_records" in metrics

    def test_cancel_task(self):
        """Test cancelling a task"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            TaskStatus,
        )

        orchestrator = ScraperOrchestrator()
        orchestrator.register_scraper("test_scraper", Mock)

        task_id = orchestrator.add_task(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        result = orchestrator.cancel_task(task_id)
        assert result is True

        task = orchestrator.task_queue.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED

    def test_set_callbacks(self):
        """Test setting callbacks"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        on_complete = Mock()
        on_error = Mock()

        orchestrator.set_callbacks(on_complete=on_complete, on_error=on_error)

        assert orchestrator._on_task_complete == on_complete
        assert orchestrator._on_task_error == on_error

    def test_start_and_stop(self):
        """Test starting and stopping orchestrator"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator(max_workers=2)

        orchestrator.start()
        assert orchestrator._running is True
        time.sleep(0.1)

        orchestrator.stop()
        assert orchestrator._running is False


class TestScheduledTask:
    """Tests for ScheduledTask class"""

    def test_scheduled_task_exists(self):
        """Test that ScheduledTask class exists"""
        from datagod.scrapers.scraper_orchestrator import ScheduledTask

        assert ScheduledTask is not None

    def test_scheduled_task_init(self):
        """Test ScheduledTask initialization"""
        from datagod.scrapers.scraper_orchestrator import ScheduledTask, TaskPriority

        task = ScheduledTask(
            schedule_id="test-123",
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=24,
        )

        assert task.schedule_id == "test-123"
        assert task.interval_hours == 24
        assert task.is_active is True

    def test_scheduled_task_should_run(self):
        """Test ScheduledTask.should_run()"""
        from datagod.scrapers.scraper_orchestrator import ScheduledTask

        task = ScheduledTask(
            schedule_id="test-123",
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=24,
        )

        # Should run immediately (next_run is set to now)
        assert task.should_run() is True

    def test_scheduled_task_update_schedule(self):
        """Test ScheduledTask.update_schedule()"""
        from datagod.scrapers.scraper_orchestrator import ScheduledTask

        task = ScheduledTask(
            schedule_id="test-123",
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=1,
        )

        old_next_run = task.next_run
        task.update_schedule()

        assert task.last_run is not None
        assert task.next_run > old_next_run


class TestScraperScheduler:
    """Tests for ScraperScheduler class"""

    def test_scraper_scheduler_exists(self):
        """Test that ScraperScheduler class exists"""
        from datagod.scrapers.scraper_orchestrator import ScraperScheduler

        assert ScraperScheduler is not None

    def test_scraper_scheduler_init(self):
        """Test ScraperScheduler initialization"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScraperScheduler,
        )

        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        assert scheduler.orchestrator == orchestrator
        assert scheduler._running is False

    def test_add_schedule(self):
        """Test adding a schedule"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScraperScheduler,
        )

        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=24,
        )

        assert schedule_id is not None
        assert schedule_id in scheduler._schedules

    def test_remove_schedule(self):
        """Test removing a schedule"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScraperScheduler,
        )

        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        result = scheduler.remove_schedule(schedule_id)
        assert result is True
        assert schedule_id not in scheduler._schedules

    def test_pause_schedule(self):
        """Test pausing a schedule"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScraperScheduler,
        )

        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        result = scheduler.pause_schedule(schedule_id)
        assert result is True
        assert scheduler._schedules[schedule_id].is_active is False

    def test_resume_schedule(self):
        """Test resuming a schedule"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScraperScheduler,
        )

        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="test_scraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        scheduler.pause_schedule(schedule_id)
        result = scheduler.resume_schedule(schedule_id)

        assert result is True
        assert scheduler._schedules[schedule_id].is_active is True

    def test_get_schedules(self):
        """Test getting all schedules"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScraperScheduler,
        )

        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        for i in range(3):
            scheduler.add_schedule(
                scraper_name=f"scraper_{i}",
                scraper_config={},
                jurisdiction_id=i,
                jurisdiction_name=f"County {i}",
            )

        schedules = scheduler.get_schedules()
        assert len(schedules) == 3


class TestScraperMonitor:
    """Tests for ScraperMonitor class"""

    def test_scraper_monitor_exists(self):
        """Test that ScraperMonitor class exists"""
        from datagod.scrapers.scraper_orchestrator import ScraperMonitor

        assert ScraperMonitor is not None

    def test_scraper_monitor_init(self):
        """Test ScraperMonitor initialization"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperMonitor,
            ScraperOrchestrator,
        )

        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        assert monitor.orchestrator == orchestrator
        assert monitor._history == []

    def test_record_snapshot(self):
        """Test recording a snapshot"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperMonitor,
            ScraperOrchestrator,
        )

        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        monitor.record_snapshot()
        assert len(monitor._history) == 1
        assert "timestamp" in monitor._history[0]
        assert "metrics" in monitor._history[0]

    def test_get_dashboard_data(self):
        """Test getting dashboard data"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperMonitor,
            ScraperOrchestrator,
        )

        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        data = monitor.get_dashboard_data()
        assert "current" in data
        assert "history" in data
        assert "summary" in data

    def test_calculate_summary(self):
        """Test calculating summary statistics"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperMonitor,
            ScraperOrchestrator,
        )

        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        summary = monitor._calculate_summary()
        assert "total_tasks_processed" in summary
        assert "success_rate" in summary
        assert "total_records" in summary


class TestGetOrchestratorFactory:
    """Tests for get_orchestrator factory function"""

    def test_get_orchestrator_exists(self):
        """Test that get_orchestrator function exists"""
        from datagod.scrapers.scraper_orchestrator import get_orchestrator

        assert callable(get_orchestrator)

    def test_get_orchestrator_returns_orchestrator(self):
        """Test that get_orchestrator returns ScraperOrchestrator"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            get_orchestrator,
        )

        orchestrator = get_orchestrator(max_workers=5)
        assert isinstance(orchestrator, ScraperOrchestrator)
        assert orchestrator.max_workers == 5

    def test_get_orchestrator_with_db_manager(self):
        """Test get_orchestrator with db_manager"""
        from datagod.scrapers.scraper_orchestrator import get_orchestrator

        mock_db = Mock()
        orchestrator = get_orchestrator(db_manager=mock_db)

        assert orchestrator.db_manager == mock_db
