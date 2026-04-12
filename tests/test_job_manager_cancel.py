from src.web import jobs


class RunningFuture:
    def done(self):
        return False

    def cancel(self):
        return False


class CompletedFuture:
    def result(self):
        return {"status": "completed", "result_path": "/tmp/results.json.gz"}


class CancelledFuture:
    def result(self):
        return {"status": "cancelled", "result_path": None}


def _make_manager() -> jobs.JobManager:
    manager = jobs.JobManager(max_workers=1)
    return manager


def _shutdown_manager(manager: jobs.JobManager) -> None:
    manager.shutdown()
    manager._manager.shutdown()


def test_cancel_marks_running_job_as_cancelled():
    manager = _make_manager()
    try:
        job_id = "running123"
        manager._jobs[job_id] = jobs.Job(id=job_id, model_name="dummy-model", testset_path="dummy.json.gz")
        jobs._write_progress(manager._progress, job_id, current=2, total=10, state="running", cancel_requested=False)
        manager._futures[job_id] = RunningFuture()

        assert manager.cancel(job_id) is True

        status = manager.get_status(job_id)
        assert status is not None
        assert status["state"] == jobs.JobState.CANCELLED.value
        assert status["progress_current"] == 2
        assert status["progress_total"] == 10
        assert dict(manager._progress[job_id])["cancel_requested"] is True
    finally:
        _shutdown_manager(manager)


def test_done_callbacks_respect_cancelled_and_completed_states():
    manager = _make_manager()
    try:
        completed_id = "completed123"
        manager._jobs[completed_id] = jobs.Job(id=completed_id, model_name="dummy-model", testset_path="dummy.json.gz")
        manager._on_done(completed_id, CompletedFuture())

        completed_status = manager.get_status(completed_id)
        assert completed_status is not None
        assert completed_status["state"] == jobs.JobState.COMPLETED.value
        assert completed_status["result_path"] == "/tmp/results.json.gz"

        cancelled_id = "cancelled123"
        manager._jobs[cancelled_id] = jobs.Job(id=cancelled_id, model_name="dummy-model", testset_path="dummy.json.gz")
        manager._jobs[cancelled_id].state = jobs.JobState.CANCELLED
        manager._on_done(cancelled_id, CancelledFuture())

        cancelled_status = manager.get_status(cancelled_id)
        assert cancelled_status is not None
        assert cancelled_status["state"] == jobs.JobState.CANCELLED.value
        assert cancelled_status["result_path"] is None
    finally:
        _shutdown_manager(manager)