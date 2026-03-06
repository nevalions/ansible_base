#!/usr/bin/env python3
"""Unit tests for WireGuard routing filter plugins.

Tests build_peers_extra_cidrs and peers_in_groups from
filter_plugins/wg_routing_filters.py.

These are the most critical routing functions in the repo:
build_peers_extra_cidrs computes which WireGuard peer owns which CIDR.
A bug here silently breaks routing for the entire cluster.

Note: All IPs and hostnames use RFC 5737 TEST-NET ranges (203.0.113.0/24,
198.51.100.0/24) and generic group names to satisfy the pre-commit security
hook. No real infrastructure values appear in this file.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "filter_plugins"))

from wg_routing_filters import (
    build_peers_extra_cidrs,
    peers_in_groups,
    validate_vip_overrides,
)


# ---------------------------------------------------------------------------
# Test fixtures — reusable peer/group definitions
#
# Naming convention (generic, no real infra names):
#   site_a_worker2   -> bay-site worker
#   site_b_worker1   -> vas-site worker
#   lb_main          -> haproxy / load-balancer
#   site_a_plane1    -> control plane node
#   site_a_bgp       -> BGP router
#   db_host          -> database host
# ---------------------------------------------------------------------------


def _make_groups(*group_defs):
    """Build an Ansible-style groups dict from (group_name, [members]) tuples."""
    return {name: members for name, members in group_defs}


def _worker_a_peer(name="worker-a2", host_group="site_a_worker2"):
    return {"name": name, "host_group": host_group}


def _worker_b_peer(name="worker-b1", host_group="site_b_worker1"):
    return {"name": name, "host_group": host_group}


def _server_peer(name="lb-main", host_group="lb_main"):
    return {"name": name, "host_group": host_group, "is_server": True}


def _db_peer(name="db-host", host_group="db"):
    return {"name": name, "host_group": host_group}


def _plane_peer(name="plane-a1", host_group="site_a_plane1"):
    return {"name": name, "host_group": host_group, "is_server": True}


# ---------------------------------------------------------------------------
# peers_in_groups tests
# ---------------------------------------------------------------------------


def test_peers_in_groups_basic():
    """Peers whose host_group members overlap target are returned."""
    peers = [
        _worker_a_peer(),
        _worker_b_peer(),
        _server_peer(),
    ]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("site_b_worker1", ["worker-b1-host"]),
        ("lb_main", ["198.51.100.132"]),
        ("kuber_small_workers", ["203.0.113.22"]),
    )
    target = ["203.0.113.22", "worker-b1-host"]  # workers
    result = peers_in_groups(peers, groups, target)
    assert "worker-a2" in result
    assert "worker-b1" in result
    assert "lb-main" not in result


def test_peers_in_groups_no_overlap():
    """No peers returned when target doesn't match any group members."""
    peers = [_worker_a_peer()]
    groups = _make_groups(("site_a_worker2", ["203.0.113.22"]))
    result = peers_in_groups(peers, groups, ["100.66.0.99"])
    assert result == []


def test_peers_in_groups_missing_host_group():
    """Peers with no host_group are silently skipped."""
    peers = [{"name": "orphan"}]
    groups = _make_groups(("site_a_worker2", ["203.0.113.22"]))
    result = peers_in_groups(peers, groups, ["203.0.113.22"])
    assert result == []


def test_peers_in_groups_empty_peers():
    """Empty peers list returns empty result."""
    result = peers_in_groups([], {}, ["203.0.113.22"])
    assert result == []


# ---------------------------------------------------------------------------
# build_peers_extra_cidrs tests — basic scenarios
# ---------------------------------------------------------------------------


def test_single_worker_gets_metallb():
    """Basic: single worker peer receives the MetalLB /24 CIDR."""
    peers = [_worker_a_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("kuber_small_workers", ["203.0.113.22"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    assert result == {"worker-a2": ["11.11.0.0/24"]}


def test_multisite_bay_gets_24_vas_empty():
    """Multi-site: bay worker gets /24, vas worker gets nothing from filter.

    Vas VIP /32 overrides are injected separately in wireguard_manage.yaml,
    not by build_peers_extra_cidrs itself.
    """
    peers = [_worker_a_peer(), _worker_b_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("site_b_worker1", ["worker-b1-host"]),
        ("kuber_small_workers", ["203.0.113.22"]),
        ("vas_workers_all", ["worker-b1-host"]),
    )
    workers = ["203.0.113.22", "worker-b1-host"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    # Only bay worker gets the /24 (first worker encountered)
    assert "11.11.0.0/24" in result.get("worker-a2", [])
    # Vas worker should NOT have the /24
    assert "11.11.0.0/24" not in result.get("worker-b1", [])


def test_first_worker_wins_metallb():
    """MetalLB /24 is assigned to FIRST worker peer only."""
    peers = [
        _worker_a_peer("worker-a", "site_a_worker2"),
        {"name": "worker-b", "host_group": "site_a_worker_office1"},
    ]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("site_a_worker_office1", ["203.0.113.31"]),
        ("kuber_small_workers", ["203.0.113.22", "203.0.113.31"]),
    )
    workers = ["203.0.113.22", "203.0.113.31"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    assert "11.11.0.0/24" in result.get("worker-a", [])
    assert "worker-b" not in result  # second worker gets nothing


def test_peer_ordering_deterministic():
    """Verify first-worker-wins is deterministic with consistent peer list order."""
    peers = [
        _worker_b_peer(),
        _worker_a_peer(),
    ]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("site_b_worker1", ["worker-b1-host"]),
    )
    workers = ["203.0.113.22", "worker-b1-host"]

    # Run multiple times to verify determinism
    for _ in range(10):
        result = build_peers_extra_cidrs(
            peers,
            groups,
            [],
            workers,
            "11.11.0.0/24",
            "100.64.0.0/16",
        )
        # worker-b1 is first in list, so it gets the /24
        assert "11.11.0.0/24" in result.get("worker-b1", [])
        assert "worker-a2" not in result


# ---------------------------------------------------------------------------
# build_peers_extra_cidrs tests — edge cases
# ---------------------------------------------------------------------------


def test_no_workers_metallb_unassigned():
    """Edge: no workers in peers list -> MetalLB CIDR unassigned."""
    peers = [_server_peer(), _plane_peer()]
    groups = _make_groups(
        ("lb_main", ["198.51.100.132"]),
        ("site_a_plane1", ["203.0.113.11"]),
    )
    workers = []  # no workers
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    # No peer should have the MetalLB CIDR
    for cidrs in result.values():
        assert "11.11.0.0/24" not in cidrs


def test_empty_metallb_cidr():
    """Edge: empty MetalLB CIDR -> no CIDR assigned to anyone."""
    peers = [_worker_a_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "",
        "100.64.0.0/16",
    )
    assert result == {}


def test_none_metallb_cidr():
    """Edge: None MetalLB CIDR -> no CIDR assigned."""
    peers = [_worker_a_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        None,
        "100.64.0.0/16",
    )
    assert result == {}


def test_db_route_added_when_no_db_peer():
    """DB WG route is added to non-DB peers when DB has no dedicated peer."""
    peers = [_worker_a_peer(), _server_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("lb_main", ["198.51.100.132"]),
    )
    workers = ["203.0.113.22"]
    db_hosts = ["198.51.100.85"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
        db_wg_route_cidr="100.65.0.5/32",
        db_hosts=db_hosts,
    )
    # Both peers should get the DB route (DB has no peer entry)
    assert "100.65.0.5/32" in result.get("worker-a2", [])
    assert "100.65.0.5/32" in result.get("lb-main", [])


def test_db_route_not_added_when_db_has_peer():
    """DB WG route is NOT added when DB has its own peer entry."""
    peers = [_worker_a_peer(), _db_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("db", ["198.51.100.85"]),
    )
    workers = ["203.0.113.22"]
    db_hosts = ["198.51.100.85"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
        db_wg_route_cidr="100.65.0.5/32",
        db_hosts=db_hosts,
    )
    # worker gets MetalLB only, not DB route
    assert "worker-a2" in result
    assert "100.65.0.5/32" not in result.get("worker-a2", [])
    # DB peer should NOT get its own route either
    assert "db-host" not in result


def test_db_route_excluded_from_db_peer():
    """Edge: DB peer never receives the DB route CIDR (would conflict)."""
    peers = [_server_peer(), _db_peer()]
    groups = _make_groups(
        ("lb_main", ["198.51.100.132"]),
        ("db", ["198.51.100.85"]),
    )
    workers = []
    db_hosts = ["198.51.100.85"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "",
        "100.64.0.0/16",
        db_wg_route_cidr="100.65.0.5/32",
        db_hosts=db_hosts,
    )
    # DB has own peer, so route not added anywhere
    assert "db-host" not in result


def test_no_db_route_cidr():
    """Edge: no DB route CIDR provided -> no DB routes added."""
    peers = [_worker_a_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
        db_wg_route_cidr=None,
        db_hosts=[],
    )
    assert result == {"worker-a2": ["11.11.0.0/24"]}


def test_peer_missing_name_skipped():
    """Peers without a name are silently skipped."""
    peers = [{"host_group": "site_a_worker2"}, _worker_a_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    assert "worker-a2" in result
    assert len(result) == 1


def test_peer_missing_host_group_skipped():
    """Peers without a host_group are silently skipped."""
    peers = [{"name": "orphan"}, _worker_a_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    assert "worker-a2" in result
    assert "orphan" not in result


def test_pod_cidr_never_assigned():
    """Pod CIDR is never added to any peer (handled by MASQUERADE)."""
    peers = [_worker_a_peer(), _server_peer()]
    groups = _make_groups(
        ("site_a_worker2", ["203.0.113.22"]),
        ("lb_main", ["198.51.100.132"]),
    )
    workers = ["203.0.113.22"]
    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
    )
    for cidrs in result.values():
        assert "100.64.0.0/16" not in cidrs


def test_full_cluster_scenario():
    """Realistic multi-site cluster with servers, workers, and DB."""
    peers = [
        _server_peer("lb-main", "lb_main"),
        {"name": "bgp-router", "host_group": "site_a_bgp", "is_server": True},
        _plane_peer("plane-a1", "site_a_plane1"),
        _worker_a_peer("worker-a2", "site_a_worker2"),
        _worker_b_peer("worker-b1", "site_b_worker1"),
        _db_peer("db-host", "db"),
    ]
    groups = _make_groups(
        ("lb_main", ["198.51.100.132"]),
        ("site_a_bgp", ["203.0.113.241"]),
        ("site_a_plane1", ["203.0.113.11"]),
        ("site_a_worker2", ["203.0.113.22"]),
        ("site_b_worker1", ["worker-b1-host"]),
        ("db", ["198.51.100.85"]),
        ("kuber_small_workers", ["203.0.113.22"]),
        ("vas_workers_all", ["worker-b1-host"]),
        ("bgp_routers", ["203.0.113.241", "198.51.100.132"]),
    )
    workers = ["203.0.113.22", "worker-b1-host"]
    db_hosts = ["198.51.100.85"]

    result = build_peers_extra_cidrs(
        peers,
        groups,
        groups["bgp_routers"],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
        db_wg_route_cidr="100.65.0.5/32",
        db_hosts=db_hosts,
    )

    # worker-a2 is first worker => gets MetalLB /24
    assert "11.11.0.0/24" in result["worker-a2"]
    # DB has own peer => no DB route added anywhere
    assert "100.65.0.5/32" not in result.get("worker-a2", [])
    # worker-b1 gets nothing from this function (vas VIP /32 injected separately)
    assert "worker-b1" not in result
    # Servers get nothing (no MetalLB, no DB route since DB has peer)
    assert "lb-main" not in result
    assert "bgp-router" not in result


def test_full_cluster_no_db_peer():
    """Realistic cluster without DB peer entry => DB route added to non-DB peers."""
    peers = [
        _server_peer("lb-main", "lb_main"),
        _worker_a_peer("worker-a2", "site_a_worker2"),
        _worker_b_peer("worker-b1", "site_b_worker1"),
        # No DB peer
    ]
    groups = _make_groups(
        ("lb_main", ["198.51.100.132"]),
        ("site_a_worker2", ["203.0.113.22"]),
        ("site_b_worker1", ["worker-b1-host"]),
        ("kuber_small_workers", ["203.0.113.22"]),
        ("vas_workers_all", ["worker-b1-host"]),
    )
    workers = ["203.0.113.22", "worker-b1-host"]
    db_hosts = ["198.51.100.85"]

    result = build_peers_extra_cidrs(
        peers,
        groups,
        [],
        workers,
        "11.11.0.0/24",
        "100.64.0.0/16",
        db_wg_route_cidr="100.65.0.5/32",
        db_hosts=db_hosts,
    )

    # worker-a2: MetalLB /24 + DB route
    assert "11.11.0.0/24" in result["worker-a2"]
    assert "100.65.0.5/32" in result["worker-a2"]
    # worker-b1: DB route only (no MetalLB since bay got it first)
    assert "100.65.0.5/32" in result["worker-b1"]
    assert "11.11.0.0/24" not in result.get("worker-b1", [])
    # lb-main: DB route only
    assert "100.65.0.5/32" in result["lb-main"]


# ---------------------------------------------------------------------------
# validate_vip_overrides tests
# ---------------------------------------------------------------------------


def test_validate_vip_valid_overrides():
    """Valid /32 overrides within pool produce no warnings."""
    warnings = validate_vip_overrides("11.11.0.0/24", ["11.11.0.3/32", "11.11.0.5/32"])
    assert warnings == []


def test_validate_vip_not_32():
    """Override that is not /32 produces a warning."""
    warnings = validate_vip_overrides("11.11.0.0/24", ["11.11.0.3/24"])
    assert len(warnings) == 1
    assert "/32" in warnings[0]


def test_validate_vip_outside_pool():
    """Override outside the MetalLB pool produces a warning."""
    warnings = validate_vip_overrides("11.11.0.0/24", ["100.65.0.1/32"])
    assert len(warnings) == 1
    assert "outside" in warnings[0]


def test_validate_vip_invalid_cidr():
    """Invalid CIDR string produces a warning."""
    warnings = validate_vip_overrides("11.11.0.0/24", ["not-a-cidr"])
    assert len(warnings) == 1
    assert "Invalid" in warnings[0]


def test_validate_vip_invalid_pool():
    """Invalid pool CIDR produces a warning."""
    warnings = validate_vip_overrides("not-a-pool", ["11.11.0.3/32"])
    assert len(warnings) == 1
    assert "Invalid MetalLB" in warnings[0]


def test_validate_vip_empty_inputs():
    """Empty inputs produce no warnings."""
    assert validate_vip_overrides("", []) == []
    assert validate_vip_overrides("11.11.0.0/24", []) == []
    assert validate_vip_overrides("", ["11.11.0.3/32"]) == []
    assert validate_vip_overrides(None, None) == []


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def _run_tests():
    """Run all tests and report results."""
    test_functions = [
        obj
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]

    passed = 0
    failed = 0
    errors = []

    for test_fn in sorted(test_functions, key=lambda f: f.__name__):
        try:
            test_fn()
            passed += 1
            print(f"  PASS: {test_fn.__name__}")
        except AssertionError as exc:
            failed += 1
            errors.append((test_fn.__name__, str(exc)))
            print(f"  FAIL: {test_fn.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            errors.append((test_fn.__name__, str(exc)))
            print(f"  ERROR: {test_fn.__name__}: {exc}")

    print(f"\nwg_routing_filters: {passed} passed, {failed} failed")

    if errors:
        print("\nFailures:")
        for name, msg in errors:
            print(f"  {name}: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    _run_tests()
