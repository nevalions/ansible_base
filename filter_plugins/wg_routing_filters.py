#!/usr/bin/env python3
"""WireGuard Routing Filters for Ansible

Helpers to compute per-peer AllowedIPs assignments based on Ansible
group membership, avoiding complex Jinja2 set operations.
"""


def peers_in_groups(wg_peers, groups_dict, target_group_members):
    """Return names of wg_peers whose host_group has members in target_group_members.

    Args:
        wg_peers: list of dicts from vault_wg_peers
        groups_dict: Ansible groups dict (groups variable)
        target_group_members: list of host names/IPs that define the target role
                              (e.g. groups['bgp_routers'] or groups['kuber_small_workers'])

    Returns:
        list of peer names whose host_group overlaps with target_group_members
    """
    target_set = set(target_group_members)
    result = []
    for peer in wg_peers:
        host_group = peer.get("host_group")
        if not host_group:
            continue
        group_members = groups_dict.get(host_group, [])
        if set(group_members) & target_set:
            result.append(peer["name"])
    return result


def build_peers_extra_cidrs(
    wg_peers,
    groups_dict,
    bgp_router_hosts,
    worker_hosts,
    metallb_pool_cidr,
    pod_cidr,
    db_wg_route_cidr=None,
    db_hosts=None,
):
    """Build vault_wg_peers_extra_cidrs dict for all peers.

    Routing ownership rules:
      - MetalLB pool CIDR: assigned to the FIRST bay-site worker peer as a /24
        catch-all.  This ensures WireGuard cryptokey routing allows MetalLB VIP
        traffic (11.11.0.x) to traverse the tunnel.  Since kube-proxy handles
        forwarding on the worker, any single bay worker is a valid entry point.
      - Vas VIP overrides: each vas-site VIP /32 is added to the FIRST vas-site
        worker peer.  WireGuard uses longest-prefix-match, so /32 beats /24.
        This ensures vas-site VIPs (e.g. 11.11.0.3, vas Traefik) are routed to
        a vas worker instead of being caught by the bay worker's /24.
      - Pod CIDR: NOT added to any peer.
        Workers apply iptables MASQUERADE (PostUp) which rewrites pod reply src IPs
        ([pod-network-cidr] range) to the worker's own WG IP ([vpn-network-cidr] range).
        HAProxy receives replies from worker /32 IPs, already in AllowedIPs. No extra CIDR needed.
      - DB WG route: only added to non-DB peers when DB has no dedicated peer entry.
        If a DB peer entry exists, its /32 is already claimed — adding elsewhere conflicts.

    Args:
        wg_peers: list of dicts from vault_wg_peers
        groups_dict: Ansible groups dict
        bgp_router_hosts: list of hosts in bgp_routers group (unused, kept for API compat)
        worker_hosts: list of hosts in kuber_small_workers + vas_workers_all
        metallb_pool_cidr: normalized MetalLB pool CIDR (e.g. "11.11.0.0/24")
        pod_cidr: Kubernetes pod CIDR (unused, kept for API compat)
        db_wg_route_cidr: optional DB WG route CIDR string
        db_hosts: list of hosts in db group (to exclude from db route)
        vas_vip_overrides: optional list of /32 CIDRs for vas-site VIPs (e.g. ["11.11.0.3/32"])
        bay_worker_hosts: optional list of hosts in bay-only worker groups
        vas_worker_hosts: optional list of hosts in vas-only worker groups

    Returns:
        dict mapping peer_name -> list of extra CIDRs
    """
    worker_set = set(worker_hosts)
    db_set = set(db_hosts or [])

    # Check if the DB group already has a dedicated peer entry.
    db_has_own_peer = any(
        set(groups_dict.get(p.get("host_group", ""), [])) & db_set
        for p in wg_peers
        if p.get("host_group")
    )

    result = {}
    metallb_assigned = False  # Track whether MetalLB pool CIDR has been assigned yet

    for peer in wg_peers:
        host_group = peer.get("host_group")
        name = peer.get("name")
        if not host_group or not name:
            continue
        group_members = set(groups_dict.get(host_group, []))
        extra = []

        # Assign MetalLB pool CIDR (/24) to the FIRST worker peer encountered.
        # WireGuard AllowedIPs are a cryptokey routing table: a packet destined
        # for 11.11.0.x must match some peer's AllowedIPs or WireGuard drops it.
        # The /24 acts as a catch-all for all MetalLB VIPs; site-specific /32
        # overrides (added separately) take precedence via longest-prefix-match.
        if metallb_pool_cidr and not metallb_assigned and (group_members & worker_set):
            extra.append(metallb_pool_cidr)
            metallb_assigned = True

        # Only add DB WG route to non-DB peers when DB has no dedicated peer entry.
        if db_wg_route_cidr and not db_has_own_peer and not (group_members & db_set):
            if db_wg_route_cidr not in extra:
                extra.append(db_wg_route_cidr)

        if extra:
            result[name] = extra

    return result


def validate_vip_overrides(metallb_pool_cidr, vas_vip_overrides):
    """Validate that vas VIP overrides are /32 entries within the MetalLB pool.

    Returns a list of warning strings (empty if all valid).
    Use in playbooks:  {{ metallb_cidr | validate_vip_overrides(vip_list) }}

    Args:
        metallb_pool_cidr: MetalLB pool CIDR string (e.g. "11.11.0.0/24")
        vas_vip_overrides: list of /32 CIDR strings (e.g. ["11.11.0.3/32"])

    Returns:
        list of warning message strings
    """
    import ipaddress

    warnings = []
    if not metallb_pool_cidr or not vas_vip_overrides:
        return warnings

    try:
        pool = ipaddress.ip_network(metallb_pool_cidr, strict=False)
    except ValueError:
        warnings.append("Invalid MetalLB pool CIDR: {}".format(metallb_pool_cidr))
        return warnings

    for vip in vas_vip_overrides:
        if not vip:
            continue
        try:
            vip_net = ipaddress.ip_network(vip, strict=False)
        except ValueError:
            warnings.append("Invalid VIP override CIDR: {}".format(vip))
            continue

        if vip_net.prefixlen != 32:
            warnings.append(
                "VIP override {} is not a /32 — must be a host route".format(vip)
            )

        if not vip_net.subnet_of(pool):
            warnings.append(
                "VIP override {} is outside MetalLB pool {} — "
                "may not need a WireGuard override".format(vip, metallb_pool_cidr)
            )

    return warnings


class FilterModule:
    def filters(self):
        return {
            "peers_in_groups": peers_in_groups,
            "build_peers_extra_cidrs": build_peers_extra_cidrs,
            "validate_vip_overrides": validate_vip_overrides,
        }
