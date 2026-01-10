"""
Scraper Orchestration System
Manages scraper execution, scheduling, task queue, and monitoring
Implements Task 4.3 of the Master Plan

Features:
- Task queue management with priority
- Worker pool for concurrent scraping
- Progress monitoring and metrics
- Error handling and retries
- Coverage tracking integration
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import PriorityQueue, Empty
from typing import Dict, Any, List, Optional, Callable, Type, Tuple
import heapq

logger = logging.getLogger(__name__)


# Coverage status constants
class CoverageStatus(Enum):
    """Coverage status for jurisdictions"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    STALE = "stale"
    NO_DATA = "no_data"
    ERROR = "error"


class CoverageGapReason(Enum):
    """Reasons why coverage may be unavailable for a jurisdiction/category"""
    NO_PUBLIC_ACCESS = "no_public_access"      # Data not publicly available
    NO_DIGITAL_RECORDS = "no_digital_records"  # Paper-only jurisdiction
    PAYWALL = "paywall"                         # Available but requires payment
    AUTH_REQUIRED = "auth_required"             # Registration/login needed
    API_UNAVAILABLE = "api_unavailable"         # No API or scraping endpoint
    RATE_LIMITED = "rate_limited"               # Temporarily blocked due to rate limits
    GEOGRAPHIC_RESTRICTION = "geo_restricted"   # IP/location restrictions
    MAINTENANCE = "maintenance"                 # Source temporarily unavailable
    DATA_FORMAT_ISSUE = "format_issue"          # Data exists but can't be parsed
    LEGAL_RESTRICTION = "legal_restriction"     # Legal/terms of service issue
    UNKNOWN = "unknown"                          # Reason not determined


@dataclass
class CoverageGap:
    """Represents a gap in coverage for a jurisdiction/category"""
    fips_code: str
    jurisdiction_name: str
    data_category: str
    reason: CoverageGapReason
    notes: str = ""
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    last_checked: datetime = field(default_factory=datetime.utcnow)
    source_url: str = ""
    alternative_source: str = ""
    estimated_availability: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'fips_code': self.fips_code,
            'jurisdiction_name': self.jurisdiction_name,
            'data_category': self.data_category,
            'reason': self.reason.value,
            'notes': self.notes,
            'discovered_at': self.discovered_at.isoformat(),
            'last_checked': self.last_checked.isoformat(),
            'source_url': self.source_url,
            'alternative_source': self.alternative_source,
            'estimated_availability': self.estimated_availability,
        }


class TaskStatus(Enum):
    """Status of a scraping task"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(Enum):
    """Priority levels for tasks"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass(order=True)
class ScrapingTask:
    """Represents a single scraping task"""
    priority: int = field(compare=True)
    task_id: str = field(compare=False)
    scraper_class: str = field(compare=False)
    scraper_config: Dict[str, Any] = field(compare=False)
    jurisdiction_id: int = field(compare=False)
    jurisdiction_name: str = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    result: Optional[Dict[str, Any]] = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    
    @classmethod
    def create(
        cls,
        scraper_class: str,
        scraper_config: Dict[str, Any],
        jurisdiction_id: int,
        jurisdiction_name: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3
    ) -> 'ScrapingTask':
        """Factory method to create a new task"""
        return cls(
            priority=priority.value,
            task_id=str(uuid.uuid4()),
            scraper_class=scraper_class,
            scraper_config=scraper_config,
            jurisdiction_id=jurisdiction_id,
            jurisdiction_name=jurisdiction_name,
            max_retries=max_retries
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'task_id': self.task_id,
            'scraper_class': self.scraper_class,
            'jurisdiction_id': self.jurisdiction_id,
            'jurisdiction_name': self.jurisdiction_name,
            'status': self.status.value,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error': self.error
        }


@dataclass
class WorkerStats:
    """Statistics for a worker thread"""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_records: int = 0
    total_time_seconds: float = 0.0
    current_task: Optional[str] = None
    is_active: bool = True
    last_activity: Optional[datetime] = None


class TaskQueue:
    """Priority-based task queue with persistence"""
    
    def __init__(self, persist_path: str = None):
        self._queue: List[ScrapingTask] = []
        self._lock = threading.Lock()
        self._persist_path = persist_path
        self._task_map: Dict[str, ScrapingTask] = {}
        
        if persist_path:
            self._load_from_disk()
    
    def put(self, task: ScrapingTask):
        """Add task to queue"""
        with self._lock:
            heapq.heappush(self._queue, task)
            self._task_map[task.task_id] = task
            task.status = TaskStatus.QUEUED
            self._persist()
    
    def get(self, timeout: float = None) -> Optional[ScrapingTask]:
        """Get highest priority task"""
        start_time = time.time()
        
        while True:
            with self._lock:
                if self._queue:
                    task = heapq.heappop(self._queue)
                    return task
            
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    return None
            
            time.sleep(0.1)
    
    def peek(self) -> Optional[ScrapingTask]:
        """Peek at highest priority task without removing"""
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None
    
    def size(self) -> int:
        """Get queue size"""
        with self._lock:
            return len(self._queue)
    
    def get_task(self, task_id: str) -> Optional[ScrapingTask]:
        """Get task by ID"""
        return self._task_map.get(task_id)
    
    def update_task(self, task: ScrapingTask):
        """Update task in map"""
        with self._lock:
            self._task_map[task.task_id] = task
            self._persist()
    
    def get_all_tasks(self) -> List[ScrapingTask]:
        """Get all tasks"""
        return list(self._task_map.values())
    
    def _persist(self):
        """Persist queue to disk"""
        if not self._persist_path:
            return
        
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'queue': [t.to_dict() for t in self._queue],
                'tasks': {k: v.to_dict() for k, v in self._task_map.items()}
            }
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist queue: {e}")
    
    def _load_from_disk(self):
        """Load queue from disk"""
        try:
            path = Path(self._persist_path)
            if not path.exists():
                return
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct tasks (simplified - would need full deserialization in production)
            logger.info(f"Loaded {len(data.get('tasks', {}))} tasks from disk")
        except Exception as e:
            logger.error(f"Failed to load queue from disk: {e}")


class ScraperOrchestrator:
    """
    Orchestrates multiple scrapers with:
    - Task queue management
    - Worker pool
    - Progress monitoring
    - Error handling and retries
    - Metrics collection
    """
    
    def __init__(
        self,
        max_workers: int = 5,
        persist_path: str = None,
        db_manager = None
    ):
        self.max_workers = max_workers
        self.db_manager = db_manager
        
        # Task queue
        self.task_queue = TaskQueue(persist_path)
        
        # Worker management
        self._executor: Optional[ThreadPoolExecutor] = None
        self._workers: Dict[str, WorkerStats] = {}
        self._futures: Dict[str, Future] = {}
        
        # Scraper registry
        self._scraper_registry: Dict[str, Type] = {}
        
        # Control flags
        self._running = False
        self._shutdown_event = threading.Event()
        
        # Metrics
        self._metrics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_records': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Callbacks
        self._on_task_complete: Optional[Callable] = None
        self._on_task_error: Optional[Callable] = None
        
        logger.info(f"Initialized ScraperOrchestrator with {max_workers} workers")
    
    def register_scraper(self, name: str, scraper_class: Type):
        """Register a scraper class"""
        self._scraper_registry[name] = scraper_class
        logger.info(f"Registered scraper: {name}")
    
    def add_task(
        self,
        scraper_name: str,
        scraper_config: Dict[str, Any],
        jurisdiction_id: int,
        jurisdiction_name: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Add a scraping task to the queue"""
        if scraper_name not in self._scraper_registry:
            raise ValueError(f"Unknown scraper: {scraper_name}")
        
        task = ScrapingTask.create(
            scraper_class=scraper_name,
            scraper_config=scraper_config,
            jurisdiction_id=jurisdiction_id,
            jurisdiction_name=jurisdiction_name,
            priority=priority
        )
        
        self.task_queue.put(task)
        self._metrics['total_tasks'] += 1
        
        logger.info(f"Added task {task.task_id} for {jurisdiction_name}")
        return task.task_id
    
    def add_bulk_tasks(
        self,
        tasks: List[Dict[str, Any]],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> List[str]:
        """Add multiple tasks at once"""
        task_ids = []
        
        for task_config in tasks:
            task_id = self.add_task(
                scraper_name=task_config['scraper_name'],
                scraper_config=task_config.get('scraper_config', {}),
                jurisdiction_id=task_config['jurisdiction_id'],
                jurisdiction_name=task_config['jurisdiction_name'],
                priority=task_config.get('priority', priority)
            )
            task_ids.append(task_id)
        
        return task_ids
    
    def start(self, blocking: bool = False):
        """Start the orchestrator"""
        if self._running:
            logger.warning("Orchestrator is already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        self._metrics['start_time'] = datetime.utcnow()
        
        # Create worker pool
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Initialize workers
        for i in range(self.max_workers):
            worker_id = f"worker-{i}"
            self._workers[worker_id] = WorkerStats(worker_id=worker_id)
        
        logger.info(f"Started orchestrator with {self.max_workers} workers")
        
        # Start worker threads
        if blocking:
            self._run_workers()
        else:
            self._worker_thread = threading.Thread(target=self._run_workers, daemon=True)
            self._worker_thread.start()
    
    def stop(self, wait: bool = True):
        """Stop the orchestrator"""
        if not self._running:
            return
        
        logger.info("Stopping orchestrator...")
        self._running = False
        self._shutdown_event.set()
        
        if wait and self._executor:
            self._executor.shutdown(wait=True)
        
        self._metrics['end_time'] = datetime.utcnow()
        logger.info("Orchestrator stopped")
    
    def _run_workers(self):
        """Main worker loop"""
        while self._running and not self._shutdown_event.is_set():
            # Get next task
            task = self.task_queue.get(timeout=1.0)
            
            if task is None:
                continue
            
            # Find available worker
            worker_id = self._get_available_worker()
            if worker_id is None:
                # Re-queue task if no workers available
                self.task_queue.put(task)
                time.sleep(0.5)
                continue
            
            # Submit task to executor
            future = self._executor.submit(self._execute_task, task, worker_id)
            self._futures[task.task_id] = future
    
    def _get_available_worker(self) -> Optional[str]:
        """Get an available worker"""
        for worker_id, stats in self._workers.items():
            if stats.is_active and stats.current_task is None:
                return worker_id
        return None
    
    def _execute_task(self, task: ScrapingTask, worker_id: str) -> Dict[str, Any]:
        """Execute a single scraping task"""
        worker = self._workers[worker_id]
        worker.current_task = task.task_id
        worker.last_activity = datetime.utcnow()
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self.task_queue.update_task(task)
        
        start_time = time.time()
        
        try:
            logger.info(f"Worker {worker_id} executing task {task.task_id} for {task.jurisdiction_name}")
            
            # Get scraper class
            scraper_class = self._scraper_registry.get(task.scraper_class)
            if not scraper_class:
                raise ValueError(f"Scraper class not found: {task.scraper_class}")
            
            # Create scraper instance
            scraper = scraper_class(
                jurisdiction_id=task.jurisdiction_id,
                jurisdiction_name=task.jurisdiction_name,
                **task.scraper_config
            )
            
            # Execute scraping
            records = scraper.scrape()
            metrics = scraper.get_metrics()
            
            # Save to database if available
            if self.db_manager and records:
                scraper.scraped_records = records
                saved_count = scraper.save_to_database(self.db_manager)
            else:
                saved_count = len(records) if records else 0
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = {
                'records_count': len(records) if records else 0,
                'saved_count': saved_count,
                'metrics': metrics
            }
            
            # Update worker stats
            worker.tasks_completed += 1
            worker.total_records += len(records) if records else 0
            worker.total_time_seconds += time.time() - start_time
            
            # Update orchestrator metrics
            self._metrics['completed_tasks'] += 1
            self._metrics['total_records'] += len(records) if records else 0
            
            # Callback
            if self._on_task_complete:
                self._on_task_complete(task)
            
            logger.info(f"Task {task.task_id} completed with {len(records) if records else 0} records")
            
            return task.result
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # Retry task
                task.status = TaskStatus.RETRY
                self.task_queue.put(task)
                logger.info(f"Task {task.task_id} queued for retry ({task.retry_count}/{task.max_retries})")
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                worker.tasks_failed += 1
                self._metrics['failed_tasks'] += 1
                
                # Callback
                if self._on_task_error:
                    self._on_task_error(task, e)
            
            return {'error': str(e)}
            
        finally:
            worker.current_task = None
            worker.last_activity = datetime.utcnow()
            self.task_queue.update_task(task)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self.task_queue.get_task(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        tasks = self.task_queue.get_all_tasks()
        
        by_status = {}
        for task in tasks:
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            'queue_size': self.task_queue.size(),
            'total_tasks': len(tasks),
            'by_status': by_status,
            'workers': {
                'total': len(self._workers),
                'active': sum(1 for w in self._workers.values() if w.current_task is not None)
            }
        }
    
    def get_worker_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all workers"""
        return {
            worker_id: {
                'tasks_completed': stats.tasks_completed,
                'tasks_failed': stats.tasks_failed,
                'total_records': stats.total_records,
                'total_time_seconds': stats.total_time_seconds,
                'current_task': stats.current_task,
                'is_active': stats.is_active,
                'avg_time_per_task': stats.total_time_seconds / max(1, stats.tasks_completed)
            }
            for worker_id, stats in self._workers.items()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics"""
        metrics = dict(self._metrics)
        
        if metrics['start_time']:
            end = metrics['end_time'] or datetime.utcnow()
            metrics['duration_seconds'] = (end - metrics['start_time']).total_seconds()
            metrics['tasks_per_minute'] = (metrics['completed_tasks'] + metrics['failed_tasks']) / max(1, metrics['duration_seconds'] / 60)
            metrics['records_per_minute'] = metrics['total_records'] / max(1, metrics['duration_seconds'] / 60)
        
        metrics['queue_status'] = self.get_queue_status()
        metrics['worker_stats'] = self.get_worker_stats()
        
        return metrics
    
    def set_callbacks(
        self,
        on_complete: Callable[[ScrapingTask], None] = None,
        on_error: Callable[[ScrapingTask, Exception], None] = None
    ):
        """Set callback functions"""
        self._on_task_complete = on_complete
        self._on_task_error = on_error

    def update_coverage(
        self,
        fips_code: str,
        data_category: str,
        status: CoverageStatus,
        record_count: int = 0,
        source_url: str = '',
        notes: str = ''
    ):
        """
        Update coverage tracking for a jurisdiction/category.

        Args:
            fips_code: 5-digit FIPS code for the jurisdiction
            data_category: Category of data (e.g., 'court_records', 'business_filings')
            status: Coverage status
            record_count: Number of records collected
            source_url: URL of the data source
            notes: Additional notes about coverage
        """
        if not self.db_manager:
            logger.warning("No db_manager configured, cannot update coverage")
            return

        try:
            # Update jurisdiction_coverage table
            coverage_data = {
                'fips_code': fips_code,
                'data_category': data_category,
                'coverage_status': status.value,
                'record_count': record_count,
                'last_scraped': datetime.utcnow(),
                'source_url': source_url,
                'notes': notes
            }

            # Use upsert pattern
            self.db_manager.upsert_coverage(coverage_data)
            logger.info(f"Updated coverage for {fips_code}/{data_category}: {status.value}")

        except Exception as e:
            logger.error(f"Failed to update coverage for {fips_code}: {e}")

    def get_coverage_summary(self) -> Dict[str, Any]:
        """
        Get coverage summary across all jurisdictions.

        Returns:
            Dictionary with coverage statistics
        """
        if not self.db_manager:
            return {'error': 'No database configured'}

        try:
            return self.db_manager.get_coverage_summary()
        except Exception as e:
            logger.error(f"Failed to get coverage summary: {e}")
            return {'error': str(e)}

    def get_coverage_gaps(
        self,
        state: str = None,
        data_category: str = None,
        min_population: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get list of jurisdictions with missing or incomplete coverage.

        Args:
            state: Filter by state (2-letter code)
            data_category: Filter by data category
            min_population: Minimum population threshold

        Returns:
            List of jurisdictions with coverage gaps
        """
        if not self.db_manager:
            return []

        try:
            return self.db_manager.get_coverage_gaps(
                state=state,
                data_category=data_category,
                min_population=min_population
            )
        except Exception as e:
            logger.error(f"Failed to get coverage gaps: {e}")
            return []

    def queue_coverage_refresh(
        self,
        fips_code: str,
        data_categories: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> List[str]:
        """
        Queue scraping tasks to refresh coverage for a jurisdiction.

        Args:
            fips_code: 5-digit FIPS code
            data_categories: List of categories to refresh (all if None)
            priority: Task priority

        Returns:
            List of task IDs queued
        """
        if not self.db_manager:
            logger.warning("No db_manager configured")
            return []

        task_ids = []

        try:
            # Get jurisdiction info
            jurisdiction = self.db_manager.get_jurisdiction_by_fips(fips_code)
            if not jurisdiction:
                logger.error(f"Jurisdiction not found for FIPS: {fips_code}")
                return []

            # Default categories if not specified
            if not data_categories:
                data_categories = [
                    'court_records', 'business_filings', 'professional_licenses',
                    'property_records', 'vital_records', 'criminal_records'
                ]

            # Queue tasks for each category
            for category in data_categories:
                scraper_name = f"{category}_scraper"
                if scraper_name in self._scraper_registry:
                    task_id = self.add_task(
                        scraper_name=scraper_name,
                        scraper_config={'data_category': category},
                        jurisdiction_id=jurisdiction['id'],
                        jurisdiction_name=jurisdiction['name'],
                        priority=priority
                    )
                    task_ids.append(task_id)
                else:
                    logger.warning(f"No scraper registered for category: {category}")

            logger.info(f"Queued {len(task_ids)} tasks for FIPS {fips_code}")
            return task_ids

        except Exception as e:
            logger.error(f"Failed to queue coverage refresh: {e}")
            return []
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        task = self.task_queue.get_task(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
            task.status = TaskStatus.CANCELLED
            self.task_queue.update_task(task)
            return True
        return False
    
    def retry_failed_tasks(self) -> int:
        """Retry all failed tasks"""
        tasks = self.task_queue.get_all_tasks()
        retried = 0

        for task in tasks:
            if task.status == TaskStatus.FAILED:
                task.status = TaskStatus.PENDING
                task.retry_count = 0
                task.error = None
                self.task_queue.put(task)
                retried += 1

        return retried

    def record_coverage_gap(
        self,
        fips_code: str,
        jurisdiction_name: str,
        data_category: str,
        reason: CoverageGapReason,
        notes: str = "",
        source_url: str = "",
        alternative_source: str = ""
    ) -> bool:
        """
        Record a coverage gap with a specific reason.

        This helps track WHY coverage is missing, enabling:
        - Prioritization of fixable gaps (auth_required vs no_public_access)
        - Gap analysis reporting
        - Alternative source identification
        - Future availability tracking

        Args:
            fips_code: 5-digit FIPS code
            jurisdiction_name: Human-readable jurisdiction name
            data_category: Category of data
            reason: Reason for the coverage gap
            notes: Additional context
            source_url: URL that was attempted
            alternative_source: Potential alternative data source

        Returns:
            True if gap was recorded successfully
        """
        if not self.db_manager:
            logger.warning("No db_manager configured, cannot record coverage gap")
            return False

        try:
            gap = CoverageGap(
                fips_code=fips_code,
                jurisdiction_name=jurisdiction_name,
                data_category=data_category,
                reason=reason,
                notes=notes,
                source_url=source_url,
                alternative_source=alternative_source
            )

            # Store gap in jurisdiction metadata
            with self.db_manager.get_session() as session:
                from datagod.models import Jurisdiction

                jurisdiction = session.query(Jurisdiction).filter_by(
                    fips_code=fips_code
                ).first()

                if jurisdiction:
                    from sqlalchemy.orm.attributes import flag_modified

                    metadata = dict(jurisdiction.jurisdiction_metadata or {})
                    coverage = dict(metadata.get('coverage', {}))

                    # Update category with gap info
                    coverage[data_category] = {
                        'status': 'gap',
                        'gap_reason': reason.value,
                        'notes': notes,
                        'source_url': source_url,
                        'alternative_source': alternative_source,
                        'last_checked': datetime.utcnow().isoformat(),
                        'record_count': 0
                    }

                    metadata['coverage'] = coverage
                    jurisdiction.jurisdiction_metadata = metadata
                    flag_modified(jurisdiction, 'jurisdiction_metadata')
                    session.commit()

                    logger.info(
                        f"Recorded coverage gap: {jurisdiction_name} / {data_category} "
                        f"- {reason.value}"
                    )
                    return True
                else:
                    logger.warning(f"Jurisdiction not found for FIPS: {fips_code}")
                    return False

        except Exception as e:
            logger.error(f"Failed to record coverage gap: {e}")
            return False

    def get_gaps_by_reason(
        self,
        reason: CoverageGapReason = None,
        state: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get coverage gaps filtered by reason.

        Args:
            reason: Filter by specific gap reason
            state: Filter by state code

        Returns:
            List of gaps with reason details
        """
        if not self.db_manager:
            return []

        try:
            gaps = []
            with self.db_manager.get_session() as session:
                from datagod.models import Jurisdiction

                query = session.query(Jurisdiction).filter(
                    Jurisdiction.fips_code.isnot(None)
                )

                if state:
                    query = query.filter(Jurisdiction.state == state)

                for j in query.all():
                    metadata = j.jurisdiction_metadata or {}
                    coverage = metadata.get('coverage', {})

                    for category, cat_data in coverage.items():
                        if isinstance(cat_data, dict) and cat_data.get('status') == 'gap':
                            gap_reason = cat_data.get('gap_reason', 'unknown')

                            # Filter by reason if specified
                            if reason and gap_reason != reason.value:
                                continue

                            gaps.append({
                                'fips_code': j.fips_code,
                                'jurisdiction_name': j.name,
                                'state': j.state,
                                'data_category': category,
                                'reason': gap_reason,
                                'notes': cat_data.get('notes', ''),
                                'source_url': cat_data.get('source_url', ''),
                                'alternative_source': cat_data.get('alternative_source', ''),
                                'last_checked': cat_data.get('last_checked'),
                            })

            return gaps

        except Exception as e:
            logger.error(f"Failed to get gaps by reason: {e}")
            return []

    def get_gap_summary(self) -> Dict[str, Any]:
        """
        Get summary of coverage gaps by reason.

        Returns:
            Dict with gap counts by reason and category
        """
        if not self.db_manager:
            return {}

        try:
            summary = {
                'total_gaps': 0,
                'by_reason': {},
                'by_category': {},
                'by_state': {},
                'fixable_gaps': 0,  # Gaps that could potentially be resolved
            }

            # Reasons that are potentially fixable
            fixable_reasons = {
                CoverageGapReason.AUTH_REQUIRED.value,
                CoverageGapReason.RATE_LIMITED.value,
                CoverageGapReason.MAINTENANCE.value,
                CoverageGapReason.DATA_FORMAT_ISSUE.value,
            }

            gaps = self.get_gaps_by_reason()

            for gap in gaps:
                summary['total_gaps'] += 1

                reason = gap['reason']
                category = gap['data_category']
                state = gap['state']

                summary['by_reason'][reason] = summary['by_reason'].get(reason, 0) + 1
                summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
                summary['by_state'][state] = summary['by_state'].get(state, 0) + 1

                if reason in fixable_reasons:
                    summary['fixable_gaps'] += 1

            return summary

        except Exception as e:
            logger.error(f"Failed to get gap summary: {e}")
            return {}


class ScheduledTask:
    """Represents a scheduled recurring task"""
    
    def __init__(
        self,
        schedule_id: str,
        scraper_name: str,
        scraper_config: Dict[str, Any],
        jurisdiction_id: int,
        jurisdiction_name: str,
        interval_hours: int = 24,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        self.schedule_id = schedule_id
        self.scraper_name = scraper_name
        self.scraper_config = scraper_config
        self.jurisdiction_id = jurisdiction_id
        self.jurisdiction_name = jurisdiction_name
        self.interval_hours = interval_hours
        self.priority = priority
        self.last_run: Optional[datetime] = None
        self.next_run: datetime = datetime.utcnow()
        self.is_active = True
    
    def should_run(self) -> bool:
        """Check if task should run"""
        return self.is_active and datetime.utcnow() >= self.next_run
    
    def update_schedule(self):
        """Update schedule after run"""
        self.last_run = datetime.utcnow()
        self.next_run = self.last_run + timedelta(hours=self.interval_hours)


class ScraperScheduler:
    """Scheduler for recurring scraping tasks"""
    
    def __init__(self, orchestrator: ScraperOrchestrator):
        self.orchestrator = orchestrator
        self._schedules: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def add_schedule(
        self,
        scraper_name: str,
        scraper_config: Dict[str, Any],
        jurisdiction_id: int,
        jurisdiction_name: str,
        interval_hours: int = 24,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Add a scheduled task"""
        schedule_id = str(uuid.uuid4())
        
        schedule = ScheduledTask(
            schedule_id=schedule_id,
            scraper_name=scraper_name,
            scraper_config=scraper_config,
            jurisdiction_id=jurisdiction_id,
            jurisdiction_name=jurisdiction_name,
            interval_hours=interval_hours,
            priority=priority
        )
        
        self._schedules[schedule_id] = schedule
        logger.info(f"Added schedule {schedule_id} for {jurisdiction_name} (every {interval_hours}h)")
        
        return schedule_id
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a scheduled task"""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a scheduled task"""
        if schedule_id in self._schedules:
            self._schedules[schedule_id].is_active = False
            return True
        return False
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a scheduled task"""
        if schedule_id in self._schedules:
            self._schedules[schedule_id].is_active = True
            return True
        return False
    
    def start(self):
        """Start the scheduler"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            for schedule_id, schedule in self._schedules.items():
                if schedule.should_run():
                    try:
                        self.orchestrator.add_task(
                            scraper_name=schedule.scraper_name,
                            scraper_config=schedule.scraper_config,
                            jurisdiction_id=schedule.jurisdiction_id,
                            jurisdiction_name=schedule.jurisdiction_name,
                            priority=schedule.priority
                        )
                        schedule.update_schedule()
                        logger.info(f"Scheduled task {schedule_id} queued for {schedule.jurisdiction_name}")
                    except Exception as e:
                        logger.error(f"Failed to queue scheduled task {schedule_id}: {e}")
            
            time.sleep(60)  # Check every minute
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules"""
        return [
            {
                'schedule_id': s.schedule_id,
                'scraper_name': s.scraper_name,
                'jurisdiction_id': s.jurisdiction_id,
                'jurisdiction_name': s.jurisdiction_name,
                'interval_hours': s.interval_hours,
                'is_active': s.is_active,
                'last_run': s.last_run.isoformat() if s.last_run else None,
                'next_run': s.next_run.isoformat()
            }
            for s in self._schedules.values()
        ]


# Monitoring Dashboard Data Provider
class ScraperMonitor:
    """Provides monitoring data for dashboard"""
    
    def __init__(self, orchestrator: ScraperOrchestrator, scheduler: ScraperScheduler = None):
        self.orchestrator = orchestrator
        self.scheduler = scheduler
        self._history: List[Dict[str, Any]] = []
        self._max_history = 1000
    
    def record_snapshot(self):
        """Record current state snapshot"""
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': self.orchestrator.get_metrics(),
            'queue_status': self.orchestrator.get_queue_status()
        }
        
        self._history.append(snapshot)
        
        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        return {
            'current': {
                'metrics': self.orchestrator.get_metrics(),
                'queue_status': self.orchestrator.get_queue_status(),
                'worker_stats': self.orchestrator.get_worker_stats()
            },
            'schedules': self.scheduler.get_schedules() if self.scheduler else [],
            'history': self._history[-100:],  # Last 100 snapshots
            'summary': self._calculate_summary()
        }
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        metrics = self.orchestrator.get_metrics()
        
        return {
            'total_tasks_processed': metrics.get('completed_tasks', 0) + metrics.get('failed_tasks', 0),
            'success_rate': (
                metrics.get('completed_tasks', 0) / 
                max(1, metrics.get('completed_tasks', 0) + metrics.get('failed_tasks', 0)) * 100
            ),
            'total_records': metrics.get('total_records', 0),
            'uptime_seconds': metrics.get('duration_seconds', 0),
            'active_workers': metrics.get('queue_status', {}).get('workers', {}).get('active', 0)
        }
    
    def export_report(self, filepath: str):
        """Export monitoring report"""
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'dashboard_data': self.get_dashboard_data()
        }
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Exported monitoring report to {filepath}")


def get_orchestrator(
    max_workers: int = 5,
    persist_path: str = None,
    db_manager = None
) -> ScraperOrchestrator:
    """Factory function to create orchestrator"""
    return ScraperOrchestrator(
        max_workers=max_workers,
        persist_path=persist_path,
        db_manager=db_manager
    )
