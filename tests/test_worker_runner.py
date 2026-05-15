import uuid

from worker.runner import coerce_task_id


def test_coerce_task_id_accepts_uuid_instance():
    task_id = uuid.uuid4()

    assert coerce_task_id(task_id) == task_id


def test_coerce_task_id_accepts_uuid_string():
    task_id = uuid.uuid4()

    assert coerce_task_id(str(task_id)) == task_id
