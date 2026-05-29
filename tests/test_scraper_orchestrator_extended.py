"""
Tests for datagod/scrapers/scraper_orchestrator.py

Comprehensive tests for the scraper orchestration system including
TaskStatus, TaskPriority, ScrapingTask, WorkerStats, TaskQueue, and ScraperOrchestrator.
"""

import os
import tempfile
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestTaskStatusEnum:
    """Tests for TaskStatus enum"""

    def test_task_status_enum_exists(self):
        """Test TaskStatus enum exists"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus is not None

    def test_task_status_pending(self):
        """Test PENDING status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.PENDING.value == "pending"

    def test_task_status_queued(self):
        """Test QUEUED status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.QUEUED.value == "queued"

    def test_task_status_running(self):
        """Test RUNNING status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.RUNNING.value == "running"

    def test_task_status_completed(self):
        """Test COMPLETED status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.COMPLETED.value == "completed"

    def test_task_status_failed(self):
        """Test FAILED status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.FAILED.value == "failed"

    def test_task_status_cancelled(self):
        """Test CANCELLED status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_retry(self):
        """Test RETRY status"""
        from datagod.scrapers.scraper_orchestrator import TaskStatus

        assert TaskStatus.RETRY.value == "retry"


class TestTaskPriorityEnum:
    """Tests for TaskPriority enum"""

    def test_task_priority_enum_exists(self):
        """Test TaskPriority enum exists"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority is not None

    def test_task_priority_critical(self):
        """Test CRITICAL priority"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority.CRITICAL.value == 1

    def test_task_priority_high(self):
        """Test HIGH priority"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority.HIGH.value == 2

    def test_task_priority_normal(self):
        """Test NORMAL priority"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority.NORMAL.value == 3

    def test_task_priority_low(self):
        """Test LOW priority"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority.LOW.value == 4

    def test_task_priority_background(self):
        """Test BACKGROUND priority"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority.BACKGROUND.value == 5

    def test_priority_ordering(self):
        """Test that priorities are properly ordered"""
        from datagod.scrapers.scraper_orchestrator import TaskPriority

        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value
        assert TaskPriority.LOW.value < TaskPriority.BACKGROUND.value


class TestScrapingTaskDataclass:
    """Tests for ScrapingTask dataclass"""

    def test_scraping_task_exists(self):
        """Test ScrapingTask dataclass exists"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask

        assert ScrapingTask is not None

    def test_create_scraping_task(self):
        """Test creating a ScrapingTask directly"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskStatus

        task = ScrapingTask(
            priority=3,
            task_id="test-123",
            scraper_class="TestScraper",
            scraper_config={"key": "value"},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
        )

        assert task.task_id == "test-123"
        assert task.scraper_class == "TestScraper"
        assert task.jurisdiction_id == 1
        assert task.status == TaskStatus.PENDING

    def test_scraping_task_factory_method(self):
        """Test ScrapingTask.create factory method"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskPriority

        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={"url": "http://example.com"},
            jurisdiction_id=123,
            jurisdiction_name="Example County",
            priority=TaskPriority.HIGH,
            max_retries=5,
        )

        assert task.scraper_class == "TestScraper"
        assert task.jurisdiction_id == 123
        assert task.priority == TaskPriority.HIGH.value
        assert task.max_retries == 5
        assert task.task_id is not None

    def test_scraping_task_to_dict(self):
        """Test ScrapingTask.to_dict method"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskPriority

        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            priority=TaskPriority.NORMAL,
        )

        result = task.to_dict()

        assert "task_id" in result
        assert "scraper_class" in result
        assert "jurisdiction_id" in result
        assert "status" in result
        assert "priority" in result
        assert "created_at" in result
        assert result["scraper_class"] == "TestScraper"

    def test_scraping_task_ordering(self):
        """Test that tasks are properly ordered by priority"""
        from datagod.scrapers.scraper_orchestrator import ScrapingTask, TaskPriority

        task_low = ScrapingTask.create("Scraper", {}, 1, "Low", TaskPriority.LOW)
        task_high = ScrapingTask.create("Scraper", {}, 2, "High", TaskPriority.HIGH)
        task_critical = ScrapingTask.create(
            "Scraper", {}, 3, "Critical", TaskPriority.CRITICAL
        )

        # Lower priority value = higher priority
        assert task_critical < task_high
        assert task_high < task_low


class TestWorkerStatsDataclass:
    """Tests for WorkerStats dataclass"""

    def test_worker_stats_exists(self):
        """Test WorkerStats dataclass exists"""
        from datagod.scrapers.scraper_orchestrator import WorkerStats

        assert WorkerStats is not None

    def test_create_worker_stats(self):
        """Test creating WorkerStats"""
        from datagod.scrapers.scraper_orchestrator import WorkerStats

        stats = WorkerStats(worker_id="worker-1")

        assert stats.worker_id == "worker-1"
        assert stats.tasks_completed == 0
        assert stats.tasks_failed == 0
        assert stats.total_records == 0
        assert stats.is_active is True
        assert stats.current_task is None

    def test_worker_stats_with_values(self):
        """Test WorkerStats with custom values"""
        from datagod.scrapers.scraper_orchestrator import WorkerStats

        stats = WorkerStats(
            worker_id="worker-2",
            tasks_completed=10,
            tasks_failed=2,
            total_records=500,
            total_time_seconds=3600.0,
            current_task="task-123",
            is_active=False,
        )

        assert stats.tasks_completed == 10
        assert stats.tasks_failed == 2
        assert stats.total_records == 500
        assert stats.current_task == "task-123"
        assert stats.is_active is False


class TestTaskQueue:
    """Tests for TaskQueue class"""

    def test_task_queue_exists(self):
        """Test TaskQueue class exists"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        assert TaskQueue is not None

    def test_create_task_queue(self):
        """Test creating a TaskQueue"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        queue = TaskQueue()
        assert queue is not None

    def test_task_queue_put_and_get(self):
        """Test putting and getting tasks from queue"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()

        task = ScrapingTask.create(
            "TestScraper", {}, 1, "Test County", TaskPriority.NORMAL
        )
        queue.put(task)

        assert queue.size() == 1

        retrieved = queue.get(timeout=0.1)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_task_queue_priority_ordering(self):
        """Test that tasks are retrieved in priority order"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()

        # Add tasks in random order
        low = ScrapingTask.create("Scraper", {}, 1, "Low", TaskPriority.LOW)
        high = ScrapingTask.create("Scraper", {}, 2, "High", TaskPriority.HIGH)
        critical = ScrapingTask.create(
            "Scraper", {}, 3, "Critical", TaskPriority.CRITICAL
        )

        queue.put(low)
        queue.put(high)
        queue.put(critical)

        # Should get critical first (lowest priority value)
        first = queue.get(timeout=0.1)
        assert first.jurisdiction_name == "Critical"

        second = queue.get(timeout=0.1)
        assert second.jurisdiction_name == "High"

        third = queue.get(timeout=0.1)
        assert third.jurisdiction_name == "Low"

    def test_task_queue_peek(self):
        """Test peeking at the queue"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()

        task = ScrapingTask.create("TestScraper", {}, 1, "Test", TaskPriority.NORMAL)
        queue.put(task)

        peeked = queue.peek()
        assert peeked is not None
        assert peeked.task_id == task.task_id

        # Peek should not remove item
        assert queue.size() == 1

    def test_task_queue_peek_empty(self):
        """Test peeking at empty queue"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        queue = TaskQueue()
        result = queue.peek()
        assert result is None

    def test_task_queue_size(self):
        """Test queue size"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()
        assert queue.size() == 0

        queue.put(ScrapingTask.create("S", {}, 1, "T1", TaskPriority.NORMAL))
        assert queue.size() == 1

        queue.put(ScrapingTask.create("S", {}, 2, "T2", TaskPriority.NORMAL))
        assert queue.size() == 2

    def test_task_queue_get_task_by_id(self):
        """Test getting task by ID from queue"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()

        task = ScrapingTask.create("TestScraper", {}, 1, "Test", TaskPriority.NORMAL)
        queue.put(task)

        found = queue.get_task(task.task_id)
        assert found is not None
        assert found.task_id == task.task_id

    def test_task_queue_get_task_not_found(self):
        """Test getting non-existent task"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        queue = TaskQueue()
        result = queue.get_task("nonexistent-id")
        assert result is None

    def test_task_queue_update_task(self):
        """Test updating task in queue"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
            TaskStatus,
        )

        queue = TaskQueue()

        task = ScrapingTask.create("TestScraper", {}, 1, "Test", TaskPriority.NORMAL)
        queue.put(task)

        # Update the task
        task.status = TaskStatus.RUNNING
        queue.update_task(task)

        found = queue.get_task(task.task_id)
        assert found.status == TaskStatus.RUNNING

    def test_task_queue_get_all_tasks(self):
        """Test getting all tasks from queue"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        queue = TaskQueue()

        queue.put(ScrapingTask.create("S", {}, 1, "T1", TaskPriority.NORMAL))
        queue.put(ScrapingTask.create("S", {}, 2, "T2", TaskPriority.NORMAL))
        queue.put(ScrapingTask.create("S", {}, 3, "T3", TaskPriority.NORMAL))

        all_tasks = queue.get_all_tasks()
        assert len(all_tasks) == 3

    def test_task_queue_get_timeout(self):
        """Test get with timeout on empty queue"""
        from datagod.scrapers.scraper_orchestrator import TaskQueue

        queue = TaskQueue()

        start = time.time()
        result = queue.get(timeout=0.2)
        elapsed = time.time() - start

        assert result is None
        assert elapsed >= 0.2

    def test_task_queue_with_persistence(self):
        """Test queue with persistence path"""
        from datagod.scrapers.scraper_orchestrator import (
            ScrapingTask,
            TaskPriority,
            TaskQueue,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "queue.json")
            queue = TaskQueue(persist_path=persist_path)

            task = ScrapingTask.create(
                "TestScraper", {}, 1, "Test", TaskPriority.NORMAL
            )
            queue.put(task)

            # Check file was created
            assert os.path.exists(persist_path)


class TestScraperOrchestrator:
    """Tests for ScraperOrchestrator class"""

    def test_scraper_orchestrator_exists(self):
        """Test ScraperOrchestrator class exists"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        assert ScraperOrchestrator is not None

    def test_create_orchestrator(self):
        """Test creating a ScraperOrchestrator"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator(max_workers=3)

        assert orchestrator is not None
        assert orchestrator.max_workers == 3

    def test_orchestrator_with_db_manager(self):
        """Test creating orchestrator with db_manager"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        mock_db = MagicMock()
        orchestrator = ScraperOrchestrator(max_workers=2, db_manager=mock_db)

        assert orchestrator.db_manager == mock_db

    def test_register_scraper(self):
        """Test registering a scraper"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("mock_scraper", MockScraper)

        assert "mock_scraper" in orchestrator._scraper_registry

    def test_add_task(self):
        """Test adding a task"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            TaskPriority,
        )

        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("mock_scraper", MockScraper)

        task_id = orchestrator.add_task(
            scraper_name="mock_scraper",
            scraper_config={"url": "http://example.com"},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            priority=TaskPriority.HIGH,
        )

        assert task_id is not None
        assert orchestrator._metrics["total_tasks"] == 1

    def test_add_task_unknown_scraper(self):
        """Test adding task with unknown scraper raises error"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        with pytest.raises(ValueError, match="Unknown scraper"):
            orchestrator.add_task(
                scraper_name="unknown_scraper",
                scraper_config={},
                jurisdiction_id=1,
                jurisdiction_name="Test",
            )

    def test_add_bulk_tasks(self):
        """Test adding multiple tasks"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            TaskPriority,
        )

        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("mock_scraper", MockScraper)

        tasks = [
            {
                "scraper_name": "mock_scraper",
                "jurisdiction_id": 1,
                "jurisdiction_name": "County 1",
            },
            {
                "scraper_name": "mock_scraper",
                "jurisdiction_id": 2,
                "jurisdiction_name": "County 2",
            },
            {
                "scraper_name": "mock_scraper",
                "jurisdiction_id": 3,
                "jurisdiction_name": "County 3",
            },
        ]

        task_ids = orchestrator.add_bulk_tasks(tasks)

        assert len(task_ids) == 3
        assert orchestrator._metrics["total_tasks"] == 3

    def test_start_and_stop(self):
        """Test starting and stopping the orchestrator"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator(max_workers=2)

        # Start non-blocking
        orchestrator.start(blocking=False)

        assert orchestrator._running is True
        assert orchestrator._executor is not None
        assert len(orchestrator._workers) == 2

        # Give it a moment to initialize
        time.sleep(0.1)

        # Stop
        orchestrator.stop(wait=True)

        assert orchestrator._running is False

    def test_start_already_running(self):
        """Test starting when already running does nothing"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator(max_workers=1)

        orchestrator.start(blocking=False)
        time.sleep(0.1)

        # Try to start again - should just return
        orchestrator.start(blocking=False)

        orchestrator.stop(wait=True)

    def test_stop_not_running(self):
        """Test stopping when not running does nothing"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        # Should not raise
        orchestrator.stop()

    def test_get_available_worker(self):
        """Test getting available worker"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            WorkerStats,
        )

        orchestrator = ScraperOrchestrator(max_workers=2)

        # Add workers manually for testing
        orchestrator._workers["worker-0"] = WorkerStats(
            worker_id="worker-0", is_active=True, current_task=None
        )
        orchestrator._workers["worker-1"] = WorkerStats(
            worker_id="worker-1", is_active=True, current_task="task-123"
        )

        available = orchestrator._get_available_worker()
        assert available == "worker-0"

    def test_get_available_worker_none_available(self):
        """Test getting worker when all are busy"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            WorkerStats,
        )

        orchestrator = ScraperOrchestrator(max_workers=2)

        # Add busy workers
        orchestrator._workers["worker-0"] = WorkerStats(
            worker_id="worker-0", is_active=True, current_task="task-1"
        )
        orchestrator._workers["worker-1"] = WorkerStats(
            worker_id="worker-1", is_active=True, current_task="task-2"
        )

        available = orchestrator._get_available_worker()
        assert available is None


class TestOrchestratorMetrics:
    """Tests for orchestrator metrics"""

    def test_orchestrator_metrics_initialized(self):
        """Test metrics are properly initialized"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        assert "total_tasks" in orchestrator._metrics
        assert "completed_tasks" in orchestrator._metrics
        assert "failed_tasks" in orchestrator._metrics
        assert "total_records" in orchestrator._metrics
        assert orchestrator._metrics["total_tasks"] == 0

    def test_metrics_update_on_add_task(self):
        """Test metrics update when adding tasks"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("mock", MockScraper)
        orchestrator.add_task("mock", {}, 1, "Test")

        assert orchestrator._metrics["total_tasks"] == 1


class TestOrchestratorCallbacks:
    """Tests for orchestrator callbacks"""

    def test_orchestrator_callbacks_initially_none(self):
        """Test callbacks are initially None"""
        from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator

        orchestrator = ScraperOrchestrator()

        assert orchestrator._on_task_complete is None
        assert orchestrator._on_task_error is None


class TestModuleImports:
    """Tests for module-level imports"""

    def test_module_imports_successfully(self):
        """Test module imports without errors"""
        from datagod.scrapers import scraper_orchestrator

        assert scraper_orchestrator is not None

    def test_all_classes_importable(self):
        """Test all main classes can be imported"""
        from datagod.scrapers.scraper_orchestrator import (
            ScraperOrchestrator,
            ScrapingTask,
            TaskPriority,
            TaskQueue,
            TaskStatus,
            WorkerStats,
        )

        assert TaskStatus is not None
        assert TaskPriority is not None
        assert ScrapingTask is not None
        assert WorkerStats is not None
        assert TaskQueue is not None
        assert ScraperOrchestrator is not None
