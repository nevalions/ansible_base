# OPNsense Hairpin NAT Fix for VAS WireGuard Network

**Status:** Resolved
**Date:** 2026-03-06
**Applies to:** Any OPNsense site where WireGuard nodes behind NAT must reach
each other via the public (WAN) IP endpoint.

## Problem

VAS WireGuard nodes behind OPNsense cannot establish WireGuard handshakes with
each other when using the public WAN IP as the endpoint. External peers from
other sites connect successfully. Same-subnet peers show `0 B received` and
no `latest handshake` in `wg show`.

### Symptoms

- `wg show wg99` shows `transfer: 0 B received, X MiB sent` for local peers
- `tcpdump -i any udp port 51840` on the destination VM shows no packets from
  local peers — only traffic from external IPs
- `tcpdump` on the source VM shows packets going **out** to the WAN IP but
  no replies coming **in**
- External peers (from other sites) work normally

## Network Topology

```text
Internet
    |
[WAN: igc1 — <wan-ip>/27, gw <wan-gw>]
    |
OPNsense
    |
    ├── [LAN: igc0 — <lan-subnet>/24]         # Management / default LAN
    ├── [VAS: igc2 — <vas-subnet>/24]          # VAS WireGuard nodes ← problem network
    └── [OPT: igc3 — <opt-subnet>/24]          # Other network
```

### Port Forward Mapping

| WAN Port | Target VM          | VM LAN IP           | WG Listen Port |
|----------|--------------------|---------------------|----------------|
| 51840    | vas-worker1        | `<vas-subnet>.31`   | 51840          |
| 51841    | vas-plane1         | `<vas-subnet>.11`   | 51840          |
| 51842    | vas-office-worker1 | `<vas-subnet>.21`   | 51840          |

## Root Cause

Two separate issues combined to break hairpin NAT:

### Issue 1: Source-Restricted Port Forward Rules Blocked Reflection

The port forward rules in OPNsense GUI had source-specific entries
(e.g., `from <external-ip>`) that generated `rdr` rules in `pfctl` only
matching those specific source IPs. Even though "allow any" rules existed,
having multiple source-specific rules for the same port caused OPNsense to
not properly generate the `from any` reflection `rdr` rules on the VAS
interface (igc2).

**Fix:** Remove the source-specific port forward rules and keep only the
`from any` rules (one per port). Use firewall pass rules for access control
instead of source restrictions on port forwards.

### Issue 2: Missing Firewall Pass Rule on VAS Interface

OPNsense auto-generates associated firewall pass rules for port forwards,
but these are created on the **WAN interface only** (igc1). For hairpin NAT
to work, the redirected traffic arriving on the **VAS interface** (igc2) also
needs a pass rule. Without it:

1. VM sends UDP to `<wan-ip>:51841` → arrives inbound on igc2 (VAS)
2. `rdr on igc2` matches → rewrites destination to `<vas-subnet>.11:51840`
3. `nat on igc2` matches → rewrites source to OPNsense VAS IP
4. **No pass rule on igc2** → packet silently dropped

**Fix:** Add an explicit firewall pass rule on the VAS interface.

## Solution Applied

### Step 1: Simplify Port Forward Rules

In **Firewall → NAT → Port Forward**, for each WG port (51840, 51841, 51842):

- Keep only **one rule per port** with source set to `*` (any)
- Protocol: **UDP only** (WireGuard does not use TCP)
- Remove duplicate source-specific rules for the same port

| Interface | Proto | Source | Dest Port | Redirect Target   | Port  | Description                     |
|-----------|-------|--------|-----------|-------------------|-------|---------------------------------|
| WAN       | UDP   | *      | 51840     | `<vas-subnet>.31` | 51840 | allow any wg vas-worker1        |
| WAN       | UDP   | *      | 51841     | `<vas-subnet>.11` | 51840 | allow any wg vas-plane1         |
| WAN       | UDP   | *      | 51842     | `<vas-subnet>.21` | 51840 | allow any wg vas-office-worker1 |

### Step 2: Add Firewall Pass Rule on VAS Interface

In **Firewall → Rules → VAS** (the interface for the WireGuard node subnet):

| Field       | Value                    |
|-------------|--------------------------|
| Action      | Pass                     |
| Interface   | VAS (igc2)               |
| Direction   | in                       |
| Protocol    | UDP                      |
| Source      | VAS net                  |
| Destination | VAS net                  |
| Dest Port   | 51840                    |
| Description | Hairpin WG all VAS nodes |

### Step 3: Ensure NAT Reflection is Enabled

In **Firewall → Settings → Advanced**, enable all three:

- [x] Reflection for port forwards
- [x] Reflection for 1:1
- [x] Automatic outbound NAT for Reflection

### Step 4: Clear Stale PF States

After applying the above, stale state entries may prevent new connections.
Clear them from OPNsense SSH:

```bash
pfctl -k <vas-subnet>.31 -k <wan-ip>
pfctl -k <vas-subnet>.11 -k <wan-ip>
pfctl -k <vas-subnet>.21 -k <wan-ip>
pfctl -k <wan-ip>
```

### Step 5: Force WireGuard Re-handshake

On each VM, force WireGuard to retry the handshake:

```bash
wg set wg99 peer <PEER_PUBLIC_KEY> endpoint <wan-ip>:<port>
```

## Diagnostic Commands

### On VMs (via SSH)

```bash
# Check WireGuard peer status — look for "latest handshake" and transfer bytes
wg show wg99

# Check if UDP packets arrive at the destination VM
sudo tcpdump -i any udp port 51840 -nn -c 20

# Check if packets leave the source VM toward the WAN IP
sudo tcpdump -i any udp and host <wan-ip> -nn -c 20

# Verify routing goes through OPNsense
ip route get <wan-ip>
# Expected: via <opnsense-vas-ip> dev <interface>

# Check for local firewall blocking
iptables -L -n -v | grep 51840
```

### On OPNsense (via SSH)

```bash
# Check OPNsense version
opnsense-version

# Verify rdr (redirect) rules exist for WG ports on ALL interfaces
pfctl -s nat | grep -E "51840|51841|51842"

# Check for "from any" rdr rules (required for hairpin)
pfctl -s nat | grep "from any" | grep -E "51840|51841|51842"

# Verify firewall pass rules exist on VAS interface (igc2)
pfctl -s rules | grep 5184

# Check NAT state table for WG connections
pfctl -s state | grep 51840 | head -20

# Check filter log for blocked packets
cat /var/log/filter/latest.log | grep 51840 | tail -10

# View generated rules (pre-pfctl compilation)
cat /tmp/rules.debug | grep -E "51840|51841|51842"

# Identify interfaces
ifconfig igc0 | grep "inet "    # LAN
ifconfig igc1 | grep "inet "    # WAN
ifconfig igc2 | grep "inet "    # VAS
ifconfig igc3 | grep "inet "    # OPT
```

### What to Look For

| Observation | Meaning |
|---|---|
| `0 B received` on `wg show` for a peer | Handshake never completed — traffic not reaching the VM |
| tcpdump on dest shows no packets from LAN peers | OPNsense is not redirecting hairpin traffic |
| tcpdump on source shows Out only, no In | OPNsense drops or misroutes the reflected packet |
| `pfctl -s nat` shows `rdr` only on igc1 (WAN) | Reflection rules not generated on VAS interface |
| `pfctl -s rules` shows pass only on igc1 | Missing firewall pass rule on VAS interface — **this was our bug** |
| `pfctl -s state` shows `NO_TRAFFIC:SINGLE` | State exists but no reply traffic — pass rule or rdr missing |
| `pfctl -s state` shows `MULTIPLE:MULTIPLE` | Healthy bidirectional connection |

## Applying to Other Sites

When setting up a new OPNsense site with WireGuard nodes behind NAT:

### Checklist

- [ ] Port forward rules use `source: *` (any), protocol `UDP`, one rule per WAN port
- [ ] NAT Reflection enabled (all three checkboxes in Firewall → Settings → Advanced)
- [ ] Firewall pass rule exists on the **node subnet interface** (not just WAN):
      `Pass | UDP | <subnet> net → <subnet> net | port 51840`
- [ ] Verify with `pfctl -s nat | grep "from any"` — rdr rules must appear on the
      node subnet interface, not just WAN
- [ ] Verify with `pfctl -s rules | grep 5184` — pass rule must appear on the node
      subnet interface (e.g., igc2), not just WAN (igc1)
- [ ] After changes: clear stale states with `pfctl -k` and force WG re-handshake
- [ ] Test: `wg show wg99` should show `latest handshake` for all peers within 2 minutes

### Common Pitfalls

1. **Source-specific port forwards suppress reflection**: If you have both `from <specific-ip>`
   and `from any` rules for the same port, the specific rules may prevent proper reflection
   rule generation. Keep only `from any` for port forwards; use firewall rules for access control.

2. **Auto-generated pass rules are WAN-only**: OPNsense creates pass rules for port forwards
   on the WAN interface. Hairpin traffic arrives on the LAN/VAS interface and needs its own
   pass rule.

3. **Stale PF states**: After fixing rules, old state entries cache the broken path. Always
   clear states with `pfctl -k` after making NAT changes.

4. **TCP/UDP vs UDP-only**: WireGuard only uses UDP. Using TCP/UDP in port forwards is
   harmless but adds unnecessary rules. Prefer UDP-only for clarity.
