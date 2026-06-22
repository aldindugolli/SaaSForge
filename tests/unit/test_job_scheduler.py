import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.core.models import JobRecord
from app.services.job_scheduler import JobScheduler


class TestJobScheduler:
    def test_enqueue_creates_record(self, app, db):
        fn = MagicMock()
        with patch.object(JobScheduler, '_queue') as mock_queue:
            mock_job = MagicMock()
            mock_job.id = "rq-job-123"
            mock_queue.return_value.enqueue.return_value = mock_job

            record = JobScheduler.enqueue("Test Job", fn, queue="test-queue")

            assert record.name == "Test Job"
            assert record.queue == "test-queue"
            assert record.status == "queued"
            assert record.rq_job_id == "rq-job-123"
            assert JobRecord.query.count() == 1

    def test_enqueue_at_creates_scheduled_record(self, app, db):
        fn = MagicMock()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        with patch.object(JobScheduler, '_queue') as mock_queue:
            mock_job = MagicMock()
            mock_job.id = "rq-job-scheduled"
            mock_queue.return_value.enqueue_at.return_value = mock_job

            record = JobScheduler.enqueue_at(future, "Scheduled Job", fn)

            assert record.name == "Scheduled Job"
            assert record.status == "scheduled"

    def test_enqueue_in(self, app, db):
        fn = MagicMock()
        with patch.object(JobScheduler, '_queue') as mock_queue:
            mock_job = MagicMock()
            mock_job.id = "rq-job-delayed"
            mock_queue.return_value.enqueue_at.return_value = mock_job

            record = JobScheduler.enqueue_in(timedelta(minutes=30), "Delayed Job", fn)

            assert record.name == "Delayed Job"
            assert record.status == "scheduled"

    def test_get_recent_jobs(self, app, db):
        fn = MagicMock()
        with patch.object(JobScheduler, '_queue') as mock_queue:
            mock_queue.return_value.enqueue.side_effect = [
                MagicMock(id="rq-recent-1"), MagicMock(id="rq-recent-2")
            ]
            JobScheduler.enqueue("Job A", fn)
            JobScheduler.enqueue("Job B", fn)

            jobs = [j for j in JobScheduler.get_recent_jobs(limit=10) if j.name.startswith("Job")]
            assert len(jobs) >= 2

    def test_double_enqueue_creates_two_records(self, app, db):
        fn = MagicMock()
        with patch.object(JobScheduler, '_queue') as mock_queue:
            mock_queue.return_value.enqueue.side_effect = [
                MagicMock(id="rq-first"), MagicMock(id="rq-second")
            ]
            JobScheduler.enqueue("First", fn)
            JobScheduler.enqueue("Second", fn)

            ours = JobRecord.query.filter(JobRecord.name.in_(["First", "Second"])).count()
            assert ours == 2
