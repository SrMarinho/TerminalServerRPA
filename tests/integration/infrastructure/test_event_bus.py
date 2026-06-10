"""Event bus integration: manager mutations actually reach subscribers."""

from src.infrastructure import events


class TestManagerPublishes:
    def test_lifecycle_emits_expected_events(self, manager, fake_task, event_sink):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.set_step(exec_id, "step1", "running")
        manager.add_log(exec_id, "msg")
        manager.complete(exec_id, {"done": True})

        types = [e["type"] for e in event_sink]
        # create() is pure DB (no event); the rest broadcast
        assert "execution:step" in types
        assert "execution:log" in types
        assert "execution:status" in types
        status_evt = next(e for e in event_sink if e["type"] == "execution:status")
        assert status_evt["status"] == "completed"
        assert status_evt["execution_id"] == exec_id

    def test_create_is_silent(self, manager, fake_task, event_sink):
        name, _state, _ = fake_task
        manager.create(name, {})
        assert event_sink == []


class TestBusRobustness:
    def test_failing_subscriber_does_not_break_others(self, manager, fake_task):
        name, _state, _ = fake_task
        good: list[dict] = []

        def boom(_event):
            raise RuntimeError("subscriber blew up")

        events.subscribe(boom)
        events.subscribe(good.append)
        try:
            exec_id = manager.create(name, {})
            manager.add_log(exec_id, "still delivered")  # must not raise
            assert any(e["type"] == "execution:log" for e in good)
        finally:
            events.unsubscribe(boom)
            events.unsubscribe(good.append)

    def test_no_subscriber_is_noop(self, manager, fake_task):
        # CLI mode: nobody subscribed → publish must be a clean no-op
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.complete(exec_id, {})  # no error despite zero subscribers

    def test_unsubscribe_stops_delivery(self, manager, fake_task):
        name, _state, _ = fake_task
        seen: list[dict] = []
        events.subscribe(seen.append)
        exec_id = manager.create(name, {})
        manager.add_log(exec_id, "first")
        events.unsubscribe(seen.append)
        manager.add_log(exec_id, "second")
        messages = [e.get("message") for e in seen if e["type"] == "execution:log"]
        assert "first" in messages
        assert "second" not in messages

    def test_duplicate_subscribe_delivers_once(self, manager, fake_task):
        name, _state, _ = fake_task
        seen: list[dict] = []
        events.subscribe(seen.append)
        events.subscribe(seen.append)  # subscribe() dedups
        try:
            exec_id = manager.create(name, {})
            manager.add_log(exec_id, "once")
            logs = [e for e in seen if e["type"] == "execution:log"]
            assert len(logs) == 1
        finally:
            events.unsubscribe(seen.append)
