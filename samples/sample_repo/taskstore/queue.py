"""A tiny FIFO queue backed by TaskStore."""

from taskstore.store import TaskStore


class TaskQueue:
    def __init__(self, store=None):
        self._store = store or TaskStore()
        self._order = []

    def enqueue(self, task_id, payload):
        self._store.add(task_id, payload)
        self._order.append(task_id)

    def dequeue(self):
        task_id = self._order.pop(0)
        return self._store.get(task_id)
