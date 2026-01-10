"""
Tests for Scraper Orchestration System
Tests task queue, worker management, and scheduling
"""

import pytest
import tempfile
import os
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from datagod.scrapers.scraper_orchestrator import (
    TaskStatus,
    TaskPriority,
    ScrapingTask,
    WorkerStats,
    TaskQueue,
)


class TestTaskStatus:
    """Tests for TaskStatus enum"""

    def test_status_values(self):
        """Test all status values exist"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.RETRY.value == "retry"


class TestTaskPriority:
    """Tests for TaskPriority enum"""

    def test_priority_ordering(self):
        """Test priority values are ordered correctly"""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value
        assert TaskPriority.LOW.value < TaskPriority.BACKGROUND.value

    def test_priority_values(self):
        """Test specific priority values"""
        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.NORMAL.value == 3
        assert TaskPriority.BACKGROUND.value == 5


class TestScrapingTask:
    """Tests for ScrapingTask dataclass"""

    def test_create_task(self):
        """Test creating a scraping task"""
        task = ScrapingTask.create(
            scraper_class="TexasAPIIntegration",
            scraper_config={"county": "Harris"},
            jurisdiction_id=1,
            jurisdiction_name="Harris County",
            priority=TaskPriority.HIGH
        )

        assert task.scraper_class == "TexasAPIIntegration"
        assert task.jurisdiction_id == 1
        assert task.jurisdiction_name == "Harris County"
        assert task.priority == TaskPriority.HIGH.value
        assert task.status == TaskStatus.PENDING
        assert task.task_id is not None
        assert task.retry_count == 0

    def test_create_task_default_priority(self):
        """Test creating task with default priority"""
        task = ScrapingTask.create(
            scraper_class="CaliforniaAPIIntegration",
            scraper_config={},
            jurisdiction_id=2,
            jurisdiction_name="Los Angeles County"
        )

        assert task.priority == TaskPriority.NORMAL.value

    def test_task_to_dict(self):
        """Test converting task to dictionary"""
        task = ScrapingTask.create(
            scraper_class="TestScraper",
            scraper_config={"key": "value"},
            jurisdiction_id=10,
            jurisdiction_name="Test County"
        )

        result = task.to_dict()

        assert result['task_id'] == task.task_id
        assert result['scraper_class'] == "TestScraper"
        assert result['jurisdiction_id'] == 10
        assert result['jurisdiction_name'] == "Test County"
        assert result['status'] == "pending"
        assert result['priority'] == 3  # NORMAL
        assert result['created_at'] is not None

    def test_task_comparison(self):
        """Test tasks are compared by priority"""
        high_priority = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test",
            priority=TaskPriority.HIGH
        )
        low_priority = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=2, jurisdiction_name="Test2",
            priority=TaskPriority.LOW
        )

        # Lower priority value = higher priority
        assert high_priority < low_priority

    def test_task_max_retries(self):
        """Test custom max retries"""
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test",
            max_retries=5
        )

        assert task.max_retries == 5


class TestWorkerStats:
    """Tests for WorkerStats dataclass"""

    def test_worker_stats_creation(self):
        """Test creating worker stats"""
        stats = WorkerStats(worker_id="worker-1")

        assert stats.worker_id == "worker-1"
        assert stats.tasks_completed == 0
        assert stats.tasks_failed == 0
        assert stats.total_records == 0
        assert stats.is_active is True

    def test_worker_stats_with_data(self):
        """Test worker stats with data"""
        stats = WorkerStats(
            worker_id="worker-2",
            tasks_completed=10,
            tasks_failed=2,
            total_records=500,
            total_time_seconds=120.5
        )

        assert stats.tasks_completed == 10
        assert stats.tasks_failed == 2
        assert stats.total_records == 500
        assert stats.total_time_seconds == 120.5


class TestTaskQueue:
    """Tests for TaskQueue class"""

    def test_queue_put_and_get(self):
        """Test putting and getting tasks from queue"""
        queue = TaskQueue()

        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        queue.put(task)

        assert queue.size() == 1

        retrieved = queue.get(timeout=1.0)
        assert retrieved.task_id == task.task_id
        assert queue.size() == 0

    def test_queue_priority_ordering(self):
        """Test tasks are retrieved by priority"""
        queue = TaskQueue()

        # Add tasks in random priority order
        low = ScrapingTask.create(
            scraper_class="Low", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Low",
            priority=TaskPriority.LOW
        )
        critical = ScrapingTask.create(
            scraper_class="Critical", scraper_config={},
            jurisdiction_id=2, jurisdiction_name="Critical",
            priority=TaskPriority.CRITICAL
        )
        normal = ScrapingTask.create(
            scraper_class="Normal", scraper_config={},
            jurisdiction_id=3, jurisdiction_name="Normal",
            priority=TaskPriority.NORMAL
        )

        queue.put(low)
        queue.put(critical)
        queue.put(normal)

        # Should get critical first (lowest priority value)
        first = queue.get(timeout=0.1)
        assert first.scraper_class == "Critical"

        second = queue.get(timeout=0.1)
        assert second.scraper_class == "Normal"

        third = queue.get(timeout=0.1)
        assert third.scraper_class == "Low"

    def test_queue_size(self):
        """Test queue size tracking"""
        queue = TaskQueue()

        assert queue.size() == 0

        for i in range(5):
            task = ScrapingTask.create(
                scraper_class="Test", scraper_config={},
                jurisdiction_id=i, jurisdiction_name=f"Test{i}"
            )
            queue.put(task)

        assert queue.size() == 5

    def test_queue_peek(self):
        """Test peeking at queue without removing"""
        queue = TaskQueue()

        task = ScrapingTask.create(
            scraper_class="PeekTest", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        queue.put(task)

        peeked = queue.peek()
        assert peeked.task_id == task.task_id
        assert queue.size() == 1  # Still in queue

    def test_queue_peek_empty(self):
        """Test peeking at empty queue"""
        queue = TaskQueue()
        assert queue.peek() is None

    def test_queue_get_task_by_id(self):
        """Test getting task by ID"""
        queue = TaskQueue()

        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        queue.put(task)

        retrieved = queue.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_queue_get_nonexistent_task(self):
        """Test getting non-existent task returns None"""
        queue = TaskQueue()
        assert queue.get_task("nonexistent-id") is None

    def test_queue_update_task(self):
        """Test updating task status"""
        queue = TaskQueue()

        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        queue.put(task)

        # Update task status
        task.status = TaskStatus.COMPLETED
        queue.update_task(task)

        retrieved = queue.get_task(task.task_id)
        assert retrieved.status == TaskStatus.COMPLETED

    def test_queue_get_all_tasks(self):
        """Test getting all tasks"""
        queue = TaskQueue()

        for i in range(3):
            task = ScrapingTask.create(
                scraper_class="Test", scraper_config={},
                jurisdiction_id=i, jurisdiction_name=f"Test{i}"
            )
            queue.put(task)

        all_tasks = queue.get_all_tasks()
        assert len(all_tasks) == 3

    def test_queue_persistence(self):
        """Test queue persistence to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "queue.json")

            # Create queue and add tasks
            queue1 = TaskQueue(persist_path=persist_path)
            task = ScrapingTask.create(
                scraper_class="Persist", scraper_config={},
                jurisdiction_id=1, jurisdiction_name="Test"
            )
            queue1.put(task)

            # Verify file was created
            assert os.path.exists(persist_path)

    def test_queue_timeout(self):
        """Test get with timeout on empty queue"""
        queue = TaskQueue()

        start = time.time()
        result = queue.get(timeout=0.2)
        elapsed = time.time() - start

        assert result is None
        assert elapsed >= 0.2

    def test_task_status_changes_on_queue(self):
        """Test task status changes to QUEUED when added"""
        queue = TaskQueue()

        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        assert task.status == TaskStatus.PENDING

        queue.put(task)
        assert task.status == TaskStatus.QUEUED


class TestTaskTimestamps:
    """Tests for task timestamp handling"""

    def test_task_created_at(self):
        """Test task has creation timestamp"""
        before = datetime.utcnow()
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        after = datetime.utcnow()

        assert before <= task.created_at <= after

    def test_task_started_at_initially_none(self):
        """Test started_at is None initially"""
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )

        assert task.started_at is None
        assert task.completed_at is None

    def test_task_dict_includes_timestamps(self):
        """Test to_dict includes timestamp fields"""
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )
        task.started_at = datetime.utcnow()
        task.completed_at = datetime.utcnow()

        result = task.to_dict()
        assert result['created_at'] is not None
        assert result['started_at'] is not None
        assert result['completed_at'] is not None


class TestTaskErrorHandling:
    """Tests for task error handling"""

    def test_task_error_field(self):
        """Test task error field"""
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )

        assert task.error is None

        task.error = "Connection timeout"
        task.status = TaskStatus.FAILED

        assert task.error == "Connection timeout"
        assert task.status == TaskStatus.FAILED

    def test_task_retry_count(self):
        """Test task retry count"""
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test",
            max_retries=3
        )

        assert task.retry_count == 0
        assert task.max_retries == 3

        task.retry_count += 1
        assert task.retry_count == 1

    def test_task_result_field(self):
        """Test task result field"""
        task = ScrapingTask.create(
            scraper_class="Test", scraper_config={},
            jurisdiction_id=1, jurisdiction_name="Test"
        )

        assert task.result is None

        task.result = {"records_scraped": 100, "new_records": 50}
        assert task.result["records_scraped"] == 100


# Import additional classes for orchestrator tests
from datagod.scrapers.scraper_orchestrator import (
    ScraperOrchestrator,
    ScheduledTask,
    ScraperScheduler,
    ScraperMonitor,
    get_orchestrator,
)


class TestScraperOrchestrator:
    """Tests for ScraperOrchestrator class"""

    def test_orchestrator_initialization(self):
        """Test orchestrator is initialized correctly"""
        orchestrator = ScraperOrchestrator(max_workers=3)

        assert orchestrator.max_workers == 3
        assert orchestrator._running is False
        assert orchestrator._metrics['total_tasks'] == 0
        assert orchestrator._metrics['completed_tasks'] == 0

    def test_orchestrator_initialization_with_persist_path(self):
        """Test orchestrator with persistence path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "queue.json")
            orchestrator = ScraperOrchestrator(
                max_workers=5,
                persist_path=persist_path
            )

            assert orchestrator.task_queue._persist_path == persist_path

    def test_register_scraper(self):
        """Test registering a scraper class"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        assert "MockScraper" in orchestrator._scraper_registry
        assert orchestrator._scraper_registry["MockScraper"] is MockScraper

    def test_add_task(self):
        """Test adding a task to the queue"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        task_id = orchestrator.add_task(
            scraper_name="MockScraper",
            scraper_config={"county": "Harris"},
            jurisdiction_id=1,
            jurisdiction_name="Harris County"
        )

        assert task_id is not None
        assert orchestrator._metrics['total_tasks'] == 1
        assert orchestrator.task_queue.size() == 1

    def test_add_task_unknown_scraper(self):
        """Test adding task with unknown scraper raises error"""
        orchestrator = ScraperOrchestrator()

        with pytest.raises(ValueError) as exc_info:
            orchestrator.add_task(
                scraper_name="UnknownScraper",
                scraper_config={},
                jurisdiction_id=1,
                jurisdiction_name="Test County"
            )

        assert "Unknown scraper" in str(exc_info.value)

    def test_add_bulk_tasks(self):
        """Test adding multiple tasks at once"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        tasks = [
            {
                'scraper_name': 'MockScraper',
                'scraper_config': {},
                'jurisdiction_id': i,
                'jurisdiction_name': f'County {i}'
            }
            for i in range(5)
        ]

        task_ids = orchestrator.add_bulk_tasks(tasks)

        assert len(task_ids) == 5
        assert orchestrator._metrics['total_tasks'] == 5

    def test_start_and_stop(self):
        """Test starting and stopping the orchestrator"""
        orchestrator = ScraperOrchestrator(max_workers=2)

        # Start non-blocking
        orchestrator.start(blocking=False)

        assert orchestrator._running is True
        assert orchestrator._executor is not None
        assert len(orchestrator._workers) == 2
        assert orchestrator._metrics['start_time'] is not None

        # Stop
        orchestrator.stop(wait=True)

        assert orchestrator._running is False
        assert orchestrator._metrics['end_time'] is not None

    def test_start_when_already_running(self):
        """Test starting when already running logs warning"""
        orchestrator = ScraperOrchestrator(max_workers=2)

        orchestrator.start(blocking=False)

        # Try to start again (should just return without error)
        orchestrator.start(blocking=False)

        orchestrator.stop(wait=True)

    def test_stop_when_not_running(self):
        """Test stopping when not running does nothing"""
        orchestrator = ScraperOrchestrator()

        # Should not raise
        orchestrator.stop()

    def test_get_task_status(self):
        """Test getting task status"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        task_id = orchestrator.add_task(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        status = orchestrator.get_task_status(task_id)

        assert status is not None
        assert status['task_id'] == task_id
        assert status['jurisdiction_name'] == "Test County"

    def test_get_task_status_nonexistent(self):
        """Test getting status of nonexistent task"""
        orchestrator = ScraperOrchestrator()

        status = orchestrator.get_task_status("nonexistent-id")
        assert status is None

    def test_get_queue_status(self):
        """Test getting queue status"""
        orchestrator = ScraperOrchestrator(max_workers=3)

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        for i in range(3):
            orchestrator.add_task(
                scraper_name="MockScraper",
                scraper_config={},
                jurisdiction_id=i,
                jurisdiction_name=f"County {i}"
            )

        status = orchestrator.get_queue_status()

        assert status['queue_size'] == 3
        assert status['total_tasks'] == 3
        assert 'by_status' in status
        assert 'workers' in status

    def test_get_worker_stats(self):
        """Test getting worker statistics"""
        orchestrator = ScraperOrchestrator(max_workers=2)

        orchestrator.start(blocking=False)

        stats = orchestrator.get_worker_stats()

        assert len(stats) == 2
        assert 'worker-0' in stats
        assert 'worker-1' in stats
        assert stats['worker-0']['tasks_completed'] == 0
        assert stats['worker-0']['is_active'] is True

        orchestrator.stop(wait=True)

    def test_get_metrics(self):
        """Test getting orchestrator metrics"""
        orchestrator = ScraperOrchestrator(max_workers=2)
        orchestrator.start(blocking=False)

        metrics = orchestrator.get_metrics()

        assert 'total_tasks' in metrics
        assert 'completed_tasks' in metrics
        assert 'failed_tasks' in metrics
        assert 'total_records' in metrics
        assert 'duration_seconds' in metrics
        assert 'queue_status' in metrics
        assert 'worker_stats' in metrics

        orchestrator.stop(wait=True)

    def test_get_metrics_no_start_time(self):
        """Test getting metrics when not started"""
        orchestrator = ScraperOrchestrator()

        metrics = orchestrator.get_metrics()

        assert 'total_tasks' in metrics
        # No duration_seconds since start_time is None
        assert 'duration_seconds' not in metrics

    def test_set_callbacks(self):
        """Test setting callback functions"""
        orchestrator = ScraperOrchestrator()

        def on_complete(task):
            pass

        def on_error(task, error):
            pass

        orchestrator.set_callbacks(on_complete=on_complete, on_error=on_error)

        assert orchestrator._on_task_complete is on_complete
        assert orchestrator._on_task_error is on_error

    def test_cancel_task(self):
        """Test canceling a pending task"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        task_id = orchestrator.add_task(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        result = orchestrator.cancel_task(task_id)

        assert result is True

        task = orchestrator.task_queue.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED

    def test_cancel_task_already_running(self):
        """Test cannot cancel running task"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        task_id = orchestrator.add_task(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        # Manually set status to RUNNING
        task = orchestrator.task_queue.get_task(task_id)
        task.status = TaskStatus.RUNNING
        orchestrator.task_queue.update_task(task)

        result = orchestrator.cancel_task(task_id)

        assert result is False

    def test_retry_failed_tasks(self):
        """Test retrying failed tasks"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)

        # Add tasks and mark some as failed
        for i in range(3):
            task_id = orchestrator.add_task(
                scraper_name="MockScraper",
                scraper_config={},
                jurisdiction_id=i,
                jurisdiction_name=f"County {i}"
            )
            if i < 2:
                task = orchestrator.task_queue.get_task(task_id)
                task.status = TaskStatus.FAILED
                orchestrator.task_queue.update_task(task)

        retried = orchestrator.retry_failed_tasks()

        assert retried == 2

    def test_get_available_worker(self):
        """Test getting available worker"""
        orchestrator = ScraperOrchestrator(max_workers=2)
        orchestrator.start(blocking=False)

        worker_id = orchestrator._get_available_worker()

        assert worker_id is not None
        assert worker_id in orchestrator._workers

        orchestrator.stop(wait=True)

    def test_get_available_worker_none_available(self):
        """Test getting worker when none available"""
        orchestrator = ScraperOrchestrator(max_workers=2)
        orchestrator.start(blocking=False)

        # Mark all workers as busy
        for stats in orchestrator._workers.values():
            stats.current_task = "some-task-id"

        worker_id = orchestrator._get_available_worker()

        assert worker_id is None

        orchestrator.stop(wait=True)


class TestScraperOrchestratorExecution:
    """Tests for orchestrator task execution"""

    def test_execute_task_success(self):
        """Test successful task execution"""
        orchestrator = ScraperOrchestrator(max_workers=1)

        class MockScraper:
            def __init__(self, jurisdiction_id, jurisdiction_name, **kwargs):
                self.jurisdiction_id = jurisdiction_id
                self.scraped_records = []

            def scrape(self):
                return [{"id": 1, "value": 100}, {"id": 2, "value": 200}]

            def get_metrics(self):
                return {"requests": 1}

            def save_to_database(self, db_manager):
                return len(self.scraped_records)

        orchestrator.register_scraper("MockScraper", MockScraper)
        orchestrator.start(blocking=False)

        task = ScrapingTask.create(
            scraper_class="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        result = orchestrator._execute_task(task, "worker-0")

        assert result['records_count'] == 2
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert orchestrator._metrics['completed_tasks'] == 1
        assert orchestrator._metrics['total_records'] == 2

        orchestrator.stop(wait=True)

    def test_execute_task_with_callback(self):
        """Test task execution triggers callback"""
        orchestrator = ScraperOrchestrator(max_workers=1)

        callback_called = []

        class MockScraper:
            def __init__(self, jurisdiction_id, jurisdiction_name, **kwargs):
                pass

            def scrape(self):
                return []

            def get_metrics(self):
                return {}

        orchestrator.register_scraper("MockScraper", MockScraper)
        orchestrator.set_callbacks(on_complete=lambda t: callback_called.append(t))
        orchestrator.start(blocking=False)

        task = ScrapingTask.create(
            scraper_class="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        orchestrator._execute_task(task, "worker-0")

        assert len(callback_called) == 1
        assert callback_called[0].task_id == task.task_id

        orchestrator.stop(wait=True)

    def test_execute_task_failure_with_retry(self):
        """Test task failure triggers retry"""
        orchestrator = ScraperOrchestrator(max_workers=1)

        class FailingScraper:
            def __init__(self, jurisdiction_id, jurisdiction_name, **kwargs):
                pass

            def scrape(self):
                raise Exception("Scraper error")

        orchestrator.register_scraper("FailingScraper", FailingScraper)
        orchestrator.start(blocking=False)

        task = ScrapingTask.create(
            scraper_class="FailingScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            max_retries=3
        )

        result = orchestrator._execute_task(task, "worker-0")

        assert 'error' in result
        # Task is re-queued, so status becomes QUEUED (put() changes status)
        assert task.status in (TaskStatus.RETRY, TaskStatus.QUEUED)
        assert task.retry_count == 1
        assert task.error == "Scraper error"

        orchestrator.stop(wait=True)

    def test_execute_task_failure_max_retries(self):
        """Test task fails permanently after max retries"""
        orchestrator = ScraperOrchestrator(max_workers=1)

        error_callback_called = []

        class FailingScraper:
            def __init__(self, jurisdiction_id, jurisdiction_name, **kwargs):
                pass

            def scrape(self):
                raise Exception("Persistent error")

        orchestrator.register_scraper("FailingScraper", FailingScraper)
        orchestrator.set_callbacks(
            on_error=lambda t, e: error_callback_called.append((t, e))
        )
        orchestrator.start(blocking=False)

        task = ScrapingTask.create(
            scraper_class="FailingScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            max_retries=3
        )
        task.retry_count = 2  # Already retried twice

        result = orchestrator._execute_task(task, "worker-0")

        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None
        assert orchestrator._metrics['failed_tasks'] == 1
        assert len(error_callback_called) == 1

        orchestrator.stop(wait=True)

    def test_execute_task_unknown_scraper_class(self):
        """Test task execution with unknown scraper class"""
        orchestrator = ScraperOrchestrator(max_workers=1)
        orchestrator.start(blocking=False)

        task = ScrapingTask.create(
            scraper_class="NonExistentScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        result = orchestrator._execute_task(task, "worker-0")

        assert 'error' in result
        assert "Scraper class not found" in result['error']

        orchestrator.stop(wait=True)

    def test_execute_task_with_db_manager(self):
        """Test task execution with database manager"""
        orchestrator = ScraperOrchestrator(max_workers=1)

        mock_db_manager = MagicMock()
        orchestrator.db_manager = mock_db_manager

        class MockScraper:
            def __init__(self, jurisdiction_id, jurisdiction_name, **kwargs):
                self.scraped_records = []

            def scrape(self):
                return [{"id": 1}]

            def get_metrics(self):
                return {}

            def save_to_database(self, db_manager):
                return 1

        orchestrator.register_scraper("MockScraper", MockScraper)
        orchestrator.start(blocking=False)

        task = ScrapingTask.create(
            scraper_class="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        result = orchestrator._execute_task(task, "worker-0")

        assert result['saved_count'] == 1

        orchestrator.stop(wait=True)


class TestScheduledTask:
    """Tests for ScheduledTask class"""

    def test_scheduled_task_creation(self):
        """Test creating a scheduled task"""
        scheduled = ScheduledTask(
            schedule_id="sched-1",
            scraper_name="TestScraper",
            scraper_config={"key": "value"},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=12
        )

        assert scheduled.schedule_id == "sched-1"
        assert scheduled.scraper_name == "TestScraper"
        assert scheduled.interval_hours == 12
        assert scheduled.is_active is True
        assert scheduled.last_run is None

    def test_should_run_active_and_due(self):
        """Test should_run when task is due"""
        scheduled = ScheduledTask(
            schedule_id="sched-1",
            scraper_name="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        # Set next_run to past
        scheduled.next_run = datetime.utcnow() - timedelta(hours=1)

        assert scheduled.should_run() is True

    def test_should_run_not_due(self):
        """Test should_run when task is not due"""
        scheduled = ScheduledTask(
            schedule_id="sched-1",
            scraper_name="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        # Set next_run to future
        scheduled.next_run = datetime.utcnow() + timedelta(hours=1)

        assert scheduled.should_run() is False

    def test_should_run_inactive(self):
        """Test should_run when task is inactive"""
        scheduled = ScheduledTask(
            schedule_id="sched-1",
            scraper_name="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        scheduled.is_active = False
        scheduled.next_run = datetime.utcnow() - timedelta(hours=1)

        assert scheduled.should_run() is False

    def test_update_schedule(self):
        """Test updating schedule after run"""
        scheduled = ScheduledTask(
            schedule_id="sched-1",
            scraper_name="TestScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=6
        )

        before_update = datetime.utcnow()
        scheduled.update_schedule()
        after_update = datetime.utcnow()

        assert scheduled.last_run is not None
        assert before_update <= scheduled.last_run <= after_update

        expected_next = scheduled.last_run + timedelta(hours=6)
        assert abs((scheduled.next_run - expected_next).total_seconds()) < 1


class TestScraperScheduler:
    """Tests for ScraperScheduler class"""

    def test_scheduler_initialization(self):
        """Test scheduler is initialized correctly"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        assert scheduler.orchestrator is orchestrator
        assert len(scheduler._schedules) == 0
        assert scheduler._running is False

    def test_add_schedule(self):
        """Test adding a schedule"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            interval_hours=24
        )

        assert schedule_id is not None
        assert schedule_id in scheduler._schedules
        assert scheduler._schedules[schedule_id].interval_hours == 24

    def test_remove_schedule(self):
        """Test removing a schedule"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        result = scheduler.remove_schedule(schedule_id)

        assert result is True
        assert schedule_id not in scheduler._schedules

    def test_remove_nonexistent_schedule(self):
        """Test removing nonexistent schedule returns False"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        result = scheduler.remove_schedule("nonexistent-id")

        assert result is False

    def test_pause_schedule(self):
        """Test pausing a schedule"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        result = scheduler.pause_schedule(schedule_id)

        assert result is True
        assert scheduler._schedules[schedule_id].is_active is False

    def test_pause_nonexistent_schedule(self):
        """Test pausing nonexistent schedule returns False"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        result = scheduler.pause_schedule("nonexistent-id")

        assert result is False

    def test_resume_schedule(self):
        """Test resuming a paused schedule"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)
        scheduler = ScraperScheduler(orchestrator)

        schedule_id = scheduler.add_schedule(
            scraper_name="MockScraper",
            scraper_config={},
            jurisdiction_id=1,
            jurisdiction_name="Test County"
        )

        scheduler.pause_schedule(schedule_id)
        result = scheduler.resume_schedule(schedule_id)

        assert result is True
        assert scheduler._schedules[schedule_id].is_active is True

    def test_resume_nonexistent_schedule(self):
        """Test resuming nonexistent schedule returns False"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        result = scheduler.resume_schedule("nonexistent-id")

        assert result is False

    def test_start_and_stop(self):
        """Test starting and stopping the scheduler"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        scheduler.start()

        assert scheduler._running is True
        assert scheduler._thread is not None

        scheduler.stop()

        assert scheduler._running is False

    def test_start_when_already_running(self):
        """Test starting when already running does nothing"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)

        scheduler.start()
        first_thread = scheduler._thread

        scheduler.start()  # Should not create new thread

        assert scheduler._thread is first_thread

        scheduler.stop()

    def test_get_schedules(self):
        """Test getting all schedules"""
        orchestrator = ScraperOrchestrator()

        class MockScraper:
            pass

        orchestrator.register_scraper("MockScraper", MockScraper)
        scheduler = ScraperScheduler(orchestrator)

        for i in range(3):
            scheduler.add_schedule(
                scraper_name="MockScraper",
                scraper_config={},
                jurisdiction_id=i,
                jurisdiction_name=f"County {i}"
            )

        schedules = scheduler.get_schedules()

        assert len(schedules) == 3
        assert all('schedule_id' in s for s in schedules)
        assert all('jurisdiction_name' in s for s in schedules)


class TestScraperMonitor:
    """Tests for ScraperMonitor class"""

    def test_monitor_initialization(self):
        """Test monitor is initialized correctly"""
        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        assert monitor.orchestrator is orchestrator
        assert monitor.scheduler is None
        assert len(monitor._history) == 0

    def test_monitor_with_scheduler(self):
        """Test monitor with scheduler"""
        orchestrator = ScraperOrchestrator()
        scheduler = ScraperScheduler(orchestrator)
        monitor = ScraperMonitor(orchestrator, scheduler)

        assert monitor.scheduler is scheduler

    def test_record_snapshot(self):
        """Test recording a state snapshot"""
        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        monitor.record_snapshot()

        assert len(monitor._history) == 1
        assert 'timestamp' in monitor._history[0]
        assert 'metrics' in monitor._history[0]
        assert 'queue_status' in monitor._history[0]

    def test_record_snapshot_trims_history(self):
        """Test snapshot history is trimmed at max size"""
        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)
        monitor._max_history = 5

        for _ in range(10):
            monitor.record_snapshot()

        assert len(monitor._history) == 5

    def test_get_dashboard_data(self):
        """Test getting dashboard data"""
        orchestrator = ScraperOrchestrator()
        orchestrator.start(blocking=False)

        scheduler = ScraperScheduler(orchestrator)
        monitor = ScraperMonitor(orchestrator, scheduler)

        data = monitor.get_dashboard_data()

        assert 'current' in data
        assert 'schedules' in data
        assert 'history' in data
        assert 'summary' in data

        assert 'metrics' in data['current']
        assert 'queue_status' in data['current']
        assert 'worker_stats' in data['current']

        orchestrator.stop(wait=True)

    def test_get_dashboard_data_no_scheduler(self):
        """Test getting dashboard data without scheduler"""
        orchestrator = ScraperOrchestrator()
        monitor = ScraperMonitor(orchestrator)

        data = monitor.get_dashboard_data()

        assert data['schedules'] == []

    def test_calculate_summary(self):
        """Test calculating summary statistics"""
        orchestrator = ScraperOrchestrator()
        orchestrator._metrics['completed_tasks'] = 8
        orchestrator._metrics['failed_tasks'] = 2
        orchestrator._metrics['total_records'] = 100
        orchestrator._metrics['start_time'] = datetime.utcnow()

        monitor = ScraperMonitor(orchestrator)
        summary = monitor._calculate_summary()

        assert summary['total_tasks_processed'] == 10
        assert summary['success_rate'] == 80.0
        assert summary['total_records'] == 100

    def test_export_report(self):
        """Test exporting monitoring report"""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = ScraperOrchestrator()
            monitor = ScraperMonitor(orchestrator)

            filepath = os.path.join(tmpdir, "report.json")
            monitor.export_report(filepath)

            assert os.path.exists(filepath)

            with open(filepath, 'r') as f:
                report = json.load(f)

            assert 'generated_at' in report
            assert 'dashboard_data' in report


class TestGetOrchestrator:
    """Tests for get_orchestrator factory function"""

    def test_get_orchestrator_default(self):
        """Test getting orchestrator with defaults"""
        orchestrator = get_orchestrator()

        assert isinstance(orchestrator, ScraperOrchestrator)
        assert orchestrator.max_workers == 5

    def test_get_orchestrator_custom_workers(self):
        """Test getting orchestrator with custom workers"""
        orchestrator = get_orchestrator(max_workers=10)

        assert orchestrator.max_workers == 10

    def test_get_orchestrator_with_persist_path(self):
        """Test getting orchestrator with persist path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "queue.json")
            orchestrator = get_orchestrator(persist_path=persist_path)

            assert orchestrator.task_queue._persist_path == persist_path

    def test_get_orchestrator_with_db_manager(self):
        """Test getting orchestrator with database manager"""
        mock_db = MagicMock()
        orchestrator = get_orchestrator(db_manager=mock_db)

        assert orchestrator.db_manager is mock_db


class TestTaskQueuePersistence:
    """Additional tests for TaskQueue persistence"""

    def test_persist_creates_parent_dirs(self):
        """Test persist creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "nested", "dir", "queue.json")
            queue = TaskQueue(persist_path=persist_path)

            task = ScrapingTask.create(
                scraper_class="Test", scraper_config={},
                jurisdiction_id=1, jurisdiction_name="Test"
            )
            queue.put(task)

            assert os.path.exists(persist_path)

    def test_load_from_disk_file_not_exists(self):
        """Test loading from non-existent file does nothing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "nonexistent.json")

            # Should not raise
            queue = TaskQueue(persist_path=persist_path)
            assert queue.size() == 0

    def test_load_from_disk_logs_info(self):
        """Test loading from disk logs info message"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = os.path.join(tmpdir, "queue.json")

            # Create file with data
            with open(persist_path, 'w') as f:
                json.dump({'queue': [], 'tasks': {'task1': {}}}, f)

            # Should log info
            queue = TaskQueue(persist_path=persist_path)
            assert queue._persist_path == persist_path


# Add test for json import in tests file
import json
