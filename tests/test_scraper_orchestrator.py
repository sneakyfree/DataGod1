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
