"""In-memory task storage."""

from __future__ import annotations


class TaskStore:
    def __init__(self):
        self._tasks = {}

    def add(self, task_id, payload):
        self._tasks[task_id] = payload

    def get(self, task_id):
        return self._tasks.get(task_id)

    def all_ids(self):
        return list(self._tasks)
