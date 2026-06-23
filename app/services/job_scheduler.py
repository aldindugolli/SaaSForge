import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.core.extensions import db, rq
from app.core.models import JobRecord

logger = logging.getLogger(__name__)


class JobScheduler:
    QUEUE_DEFAULT = "saasforge-jobs"

    SCHEDULES = {
        "hourly": timedelta(hours=1),
        "daily": timedelta(hours=24),
        "weekly": timedelta(weeks=1),
    }

    @staticmethod
    def _queue(name: str = QUEUE_DEFAULT):
        if rq is None:
            raise RuntimeError("RQ is not available (flask_rq2 import failed)")
        return rq.get_queue(name)

    @staticmethod
    def enqueue(name: str, fn: Callable, *args, queue: str = QUEUE_DEFAULT, **kwargs) -> JobRecord:
        job = JobScheduler._queue(queue).enqueue(fn, *args, **kwargs)
        record = JobRecord(
            name=name,
            queue=queue,
            status="queued",
            rq_job_id=job.id,
            scheduled_at=datetime.now(UTC),
        )
        db.session.add(record)
        db.session.commit()
        logger.info("Enqueued job %s (rq_id=%s)", name, job.id)
        return record

    @staticmethod
    def enqueue_at(delivery_timestamp: datetime, name: str, fn: Callable, *args, queue: str = QUEUE_DEFAULT, **kwargs) -> JobRecord:
        job = JobScheduler._queue(queue).enqueue_at(delivery_timestamp, fn, *args, **kwargs)
        record = JobRecord(
            name=name,
            queue=queue,
            status="scheduled",
            rq_job_id=job.id,
            scheduled_at=delivery_timestamp,
        )
        db.session.add(record)
        db.session.commit()
        logger.info("Scheduled job %s at %s (rq_id=%s)", name, delivery_timestamp, job.id)
        return record

    @staticmethod
    def enqueue_in(time_delta: timedelta, name: str, fn: Callable, *args, queue: str = QUEUE_DEFAULT, **kwargs) -> JobRecord:
        delivery = datetime.now(UTC) + time_delta
        return JobScheduler.enqueue_at(delivery, name, fn, *args, queue=queue, **kwargs)

    @staticmethod
    def get_status(rq_job_id: str) -> str | None:
        if rq is None:
            return None
        try:
            from rq.job import Job
            job = Job.fetch(rq_job_id, connection=rq.get_connection())
            return job.get_status()
        except Exception:
            return None

    @staticmethod
    def cancel(rq_job_id: str) -> bool:
        if rq is None:
            return False
        try:
            from rq.job import Job
            job = Job.fetch(rq_job_id, connection=rq.get_connection())
            job.cancel()
            JobRecord.query.filter_by(rq_job_id=rq_job_id).update({"status": "canceled"})
            db.session.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_recent_jobs(limit: int = 50) -> list:
        return JobRecord.query.order_by(JobRecord.created_at.desc()).limit(limit).all()


class JobMonitorHooks:
    @staticmethod
    def on_success(job, connection, result, *args, **kwargs):
        record = JobRecord.query.filter_by(rq_job_id=job.id).first()
        if record:
            record.status = "completed"
            record.finished_at = datetime.now(UTC)
            record.result = result if isinstance(result, dict) else {"result": str(result)}
            db.session.commit()

    @staticmethod
    def on_failure(job, connection, type, value, traceback):
        record = JobRecord.query.filter_by(rq_job_id=job.id).first()
        if record:
            record.status = "failed"
            record.finished_at = datetime.now(UTC)
            record.error = str(value)
            db.session.commit()
