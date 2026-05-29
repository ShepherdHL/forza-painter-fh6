from __future__ import annotations

from resource_monitor import ResourceMonitorBackend, evaluate_heat_state, unavailable_snapshot


def test_unavailable_snapshot_afterburner_message():
    snapshot = unavailable_snapshot("afterburner")
    assert snapshot.backend == "unavailable"
    assert snapshot.message == "afterburner"
    assert snapshot.gpu_temp_c is None


def test_evaluate_heat_state_warning():
    snapshot = unavailable_snapshot(None)
    snapshot = snapshot.__class__(
        cpu_load_pct=10.0,
        cpu_clock_mhz=3000.0,
        cpu_temp_c=82.0,
        gpu_load_pct=20.0,
        gpu_clock_mhz=1500.0,
        gpu_temp_c=70.0,
        backend="afterburner",
    )
    assert evaluate_heat_state(snapshot) == "warning"


def test_temp_status_message_key():
    from resource_monitor import temp_status_message_key

    assert temp_status_message_key(50.0) == "resource_temp_nominal"
    assert temp_status_message_key(82.0) == "resource_temp_warning"
    assert temp_status_message_key(92.0) == "resource_temp_critical"
    assert temp_status_message_key(None) is None


def test_resource_monitor_backend_windows_only(monkeypatch):
    backend = ResourceMonitorBackend()
    monkeypatch.setattr("resource_monitor.os.name", "posix")
    snapshot = backend.poll()
    assert snapshot.backend == "unavailable"
