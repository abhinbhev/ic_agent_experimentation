"""Tests for unified_domain.observability — EventBus and tree_builder."""

from __future__ import annotations

import threading

from unified_domain.observability import EventBus, build_tree
from unified_domain.observability import instrumentation as obs


# --------------------------------------------------------------------- #
# EventBus
# --------------------------------------------------------------------- #


def test_event_bus_emit_and_snapshot():
    bus = EventBus()
    bus.emit("root", None, "root", "asked", label="hello")
    bus.emit("SR1", "root", "super-round", "running", label="Super-Round 1")
    snap = bus.snapshot()
    assert len(snap) == 2
    assert snap[0].node_id == "root"
    assert snap[1].parent_id == "root"


def test_event_bus_snapshot_is_a_copy():
    bus = EventBus()
    bus.emit("a", None, "root", "asked")
    snap = bus.snapshot()
    bus.emit("b", "a", "super-round", "running")
    assert len(snap) == 1
    assert len(bus.snapshot()) == 2


def test_event_bus_version_advances():
    bus = EventBus()
    v0 = bus.version
    bus.emit("a", None, "root", "asked")
    assert bus.version == v0 + 1
    bus.emit("b", "a", "super-round", "running")
    assert bus.version == v0 + 2


def test_event_bus_is_thread_safe():
    bus = EventBus()
    n_threads = 8
    per_thread = 200

    def worker(tid: int) -> None:
        for i in range(per_thread):
            bus.emit(f"n-{tid}-{i}", "root", "leaf", "asked")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(bus.snapshot()) == n_threads * per_thread


# --------------------------------------------------------------------- #
# tree_builder
# --------------------------------------------------------------------- #


def test_build_tree_empty():
    assert build_tree([]) is None


def test_build_tree_single_super_round():
    bus = EventBus()
    obs.emit_root(bus, "What happened with Brahma?")
    obs.emit_super_round_start(bus, 1, sublabel="Initial")
    tree = build_tree(bus.snapshot())
    assert tree is not None
    assert tree["id"] == "root"
    assert tree["kind"] == "root"
    assert tree["label"] == "What happened with Brahma?"
    assert len(tree["children"]) == 1
    sr = tree["children"][0]
    assert sr["id"] == "SR1"
    assert sr["kind"] == "super-round"
    assert sr["round"] == 1
    assert sr["sublabel"] == "Initial"


def test_build_tree_latest_status_wins():
    bus = EventBus()
    obs.emit_root(bus, "Q")
    bus.emit("SR1", "root", "super-round", "running", label="Super-Round 1")
    bus.emit("SR1", "root", "super-round", "answered", label="Super-Round 1")
    tree = build_tree(bus.snapshot())
    assert tree["children"][0]["status"] == "answered"


def test_build_tree_preserves_child_insertion_order():
    bus = EventBus()
    obs.emit_root(bus, "Q")
    bus.emit("SR1", "root", "super-round", "running", label="r1")
    # Children appear in the order they were first emitted.
    bus.emit("P1", "SR1", "super-probe", "asked", label="probe 1")
    bus.emit("P2", "SR1", "super-probe", "asked", label="probe 2")
    bus.emit("P3", "SR1", "super-probe", "asked", label="probe 3")
    tree = build_tree(bus.snapshot())
    probe_ids = [c["id"] for c in tree["children"][0]["children"]]
    assert probe_ids == ["P1", "P2", "P3"]


def test_build_tree_two_super_rounds_under_root():
    bus = EventBus()
    obs.emit_root(bus, "Q")
    obs.emit_super_round_start(bus, 1)
    obs.emit_super_round_done(bus, 1)
    obs.emit_super_round_start(bus, 2)
    tree = build_tree(bus.snapshot())
    assert [c["id"] for c in tree["children"]] == ["SR1", "SR2"]
    assert tree["children"][0]["status"] == "answered"
    assert tree["children"][1]["status"] == "running"


# --------------------------------------------------------------------- #
# instrumentation ID helpers
# --------------------------------------------------------------------- #


def test_short_domain_known_overrides():
    assert obs.short_domain("gai_copilot_marketing_brand_guidance_ghq") == "bg"
    assert obs.short_domain("gai_copilot_marketing_category_ghq") == "cat"


def test_short_domain_fallback():
    assert obs.short_domain("my_custom_domain_id") == "mcdi"


def test_domain_node_id_format():
    assert obs.domain_node_id("P1", "gai_copilot_marketing_brand_guidance_ghq") == "P1-bg"


def test_emitters_no_op_when_bus_is_none():
    # Must not raise — None-safety is critical for tests that don't care
    # about observability.
    obs.emit_root(None, "Q")
    obs.emit_super_round_start(None, 1)
    obs.emit_super_round_done(None, 1)
    obs.emit_super_probe_status(None, "P1", "running")
    obs.emit_domain_status(None, "P1", "any_domain", "running")
    obs.emit_root_answered(None, "answer")
