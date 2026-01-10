#!/usr/bin/env python3
"""
Test Enhanced Scrapers System
Demonstrates the complete scraper orchestration system
"""

import logging
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper, ScraperType, ProxyConfig, JurisdictionScraper
from datagod.scrapers.scraper_orchestrator import (
    ScraperOrchestrator,
    ScraperScheduler,
    ScraperMonitor,
    TaskPriority
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_enhanced_base_scraper():
    """Test the enhanced base scraper functionality"""
    print("="*80)
    print("TESTING ENHANCED BASE SCRAPER")
    print("="*80)

    # Create a concrete implementation for testing
    class TestScraper(EnhancedBaseScraper):
        def scrape(self, **kwargs):
            return []

        def parse(self, response):
            return []

    # Create scraper instance
    scraper = TestScraper(
        base_url="https://httpbin.org",
        scraper_type=ScraperType.SIMPLE,
        rate_limit=2.0,
        timeout=10,
        cache_enabled=True,
        cache_ttl=300
    )

    print("1. Testing basic HTTP requests...")

    # Test basic request
    response = scraper._make_request("https://httpbin.org/get", params={'test': 'value'})
    print(f"   ✓ Basic request: {'SUCCESS' if response.get('success') else 'FAILED'}")

    # Test caching
    print("2. Testing request caching...")
    start_time = time.time()
    response2 = scraper._make_request("https://httpbin.org/get", params={'test': 'value'})
    cache_time = time.time() - start_time
    print(".4f")

    # Test concurrent requests
    print("3. Testing concurrent requests...")
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1"
    ]
    start_time = time.time()
    results = scraper.scrape_concurrent(urls, max_workers=3)
    concurrent_time = time.time() - start_time
    print(".2f")

    # Test proxy setup
    print("4. Testing proxy configuration...")
    proxies = [
        {'host': 'proxy1.example.com', 'port': 8080, 'protocol': 'http'},
        {'host': 'proxy2.example.com', 'port': 8080, 'protocol': 'https'}
    ]
    scraper.add_proxies(proxies)
    print(f"   ✓ Added {len(proxies)} proxies")

    # Get metrics
    metrics = scraper.get_metrics()
    print("5. Scraper metrics:")
    print(f"   ✓ Total requests: {metrics['total_requests']}")
    print(".2f")
    print(f"   ✓ Cache enabled: {scraper.cache_enabled}")

    return scraper


def test_scraper_orchestrator():
    """Test the scraper orchestrator system"""
    print("\n" + "="*80)
    print("TESTING SCRAPER ORCHESTRATOR")
    print("="*80)

    # Create orchestrator
    orchestrator = ScraperOrchestrator(
        max_workers=2,
        persist_path="data/scraper_queue.json"
    )

    print("1. Registering scrapers...")

    # Register mock scrapers for testing
    class MockScraper(JurisdictionScraper):
        def scrape(self, **kwargs):
            # Simulate scraping by returning mock data
            return [
                {
                    'type': 'property_transfer',
                    'property_id': f'PROP-{i}',
                    'address': f'123 Main St #{i}',
                    'grantor': 'John Doe',
                    'grantee': 'Jane Smith',
                    'amount': 250000 + (i * 10000),
                    'date': datetime.utcnow().date().isoformat()
                }
                for i in range(1, 6)
            ]

        def parse(self, response):
            # Mock parse method
            return self.scrape()

    orchestrator.register_scraper('mock_texas_scraper', MockScraper)
    print("   ✓ Registered mock Texas scraper")

    print("2. Adding scraping tasks...")

    # Add some tasks
    task_ids = []
    for i in range(3):
        task_id = orchestrator.add_task(
            scraper_name='mock_texas_scraper',
            scraper_config={
                'county_name': f'County{i}',
                'rate_limit': 1.0
            },
            jurisdiction_id=100 + i,
            jurisdiction_name=f'Texas County {i}',
            priority=TaskPriority.NORMAL
        )
        task_ids.append(task_id)
        print(f"   ✓ Added task {task_id}")

    print("3. Starting orchestrator...")
    orchestrator.start()

    # Wait for tasks to complete
    print("4. Waiting for tasks to complete...")
    start_time = time.time()
    timeout = 30  # 30 seconds timeout

    while time.time() - start_time < timeout:
        queue_status = orchestrator.get_queue_status()
        if queue_status['queue_size'] == 0:
            break
        time.sleep(2)

    orchestrator.stop()

    print("5. Final results:")
    metrics = orchestrator.get_metrics()
    print(f"   ✓ Tasks completed: {metrics['completed_tasks']}")
    print(f"   ✓ Tasks failed: {metrics['failed_tasks']}")
    print(f"   ✓ Total records: {metrics['total_records']}")
    print(".2f")

    return orchestrator


def test_scheduler():
    """Test the scraper scheduler"""
    print("\n" + "="*80)
    print("TESTING SCRAPER SCHEDULER")
    print("="*80)

    orchestrator = ScraperOrchestrator(max_workers=1)
    scheduler = ScraperScheduler(orchestrator)

    print("1. Adding scheduled tasks...")

    # Add a schedule that runs every hour
    schedule_id = scheduler.add_schedule(
        scraper_name='mock_texas_scraper',
        scraper_config={'county_name': 'Harris'},
        jurisdiction_id=200,
        jurisdiction_name='Harris County, TX',
        interval_hours=1,  # Every hour
        priority=TaskPriority.NORMAL
    )
    print(f"   ✓ Added schedule {schedule_id}")

    print("2. Starting scheduler...")
    scheduler.start()

    # Let it run briefly
    time.sleep(2)

    scheduler.stop()

    print("3. Schedule status:")
    schedules = scheduler.get_schedules()
    for sched in schedules:
        print(f"   ✓ {sched['jurisdiction_name']}: {sched['interval_hours']}h interval")

    return scheduler


def test_monitoring():
    """Test the monitoring dashboard"""
    print("\n" + "="*80)
    print("TESTING MONITORING DASHBOARD")
    print("="*80)

    orchestrator = ScraperOrchestrator(max_workers=1)
    monitor = ScraperMonitor(orchestrator)

    print("1. Recording snapshots...")

    # Record some snapshots
    for i in range(3):
        monitor.record_snapshot()
        time.sleep(1)

    print("   ✓ Recorded monitoring snapshots")

    print("2. Generating dashboard data...")
    dashboard_data = monitor.get_dashboard_data()

    print("3. Dashboard summary:")
    summary = dashboard_data['summary']
    print(f"   ✓ Total tasks processed: {summary['total_tasks_processed']}")
    print(".2f")
    print(f"   ✓ Total records: {summary['total_records']}")
    print(".2f")

    print("4. Exporting monitoring report...")
    monitor.export_report("data/scraper_monitoring_report.json")
    print("   ✓ Exported to data/scraper_monitoring_report.json")

    return monitor


def run_comprehensive_test():
    """Run a comprehensive test of the entire scraper system"""
    print("\n" + "="*100)
    print("COMPREHENSIVE SCRAPER SYSTEM TEST")
    print("="*100)

    try:
        # Test individual components
        scraper = test_enhanced_base_scraper()
        orchestrator = test_scraper_orchestrator()
        scheduler = test_scheduler()
        monitor = test_monitoring()

        print("\n" + "="*100)
        print("FINAL SYSTEM STATUS")
        print("="*100)

        # Final metrics
        final_metrics = orchestrator.get_metrics()
        print("Overall System Metrics:")
        print(f"  • Total Tasks: {final_metrics['total_tasks']}")
        print(f"  • Completed Tasks: {final_metrics['completed_tasks']}")
        print(f"  • Failed Tasks: {final_metrics['failed_tasks']}")
        print(".2f")
        print(f"  • Total Records: {final_metrics['total_records']}")
        print(".2f")

        queue_status = final_metrics['queue_status']
        print(f"  • Workers Total: {queue_status['workers']['total']}")
        print(f"  • Workers Active: {queue_status['workers']['active']}")

        print("\n✅ ENHANCED SCRAPER SYSTEM TEST COMPLETED SUCCESSFULLY")
        print("\nNext Steps:")
        print("1. Configure real jurisdiction scrapers")
        print("2. Set up proxy services for production")
        print("3. Deploy orchestrator with persistent storage")
        print("4. Configure monitoring alerts")
        print("5. Scale worker pool based on load")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_comprehensive_test()
