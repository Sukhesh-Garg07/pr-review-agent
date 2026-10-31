from taskstore.store import TaskStore


def test_add_and_get():
    store = TaskStore()
    store.add("t1", {"job": "resize"})
    assert store.get("t1") == {"job": "resize"}


def test_all_ids():
    store = TaskStore()
    store.add("a", {})
    store.add("b", {})
    assert store.all_ids() == ["a", "b"]
