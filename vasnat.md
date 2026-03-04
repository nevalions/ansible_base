Plan to Fix
There are a few options:

1. Fix OPNsense NAT reflection settings — In OPNsense under Firewall > Settings > Advanced:
   - Check that "Reflection for port forwards" is set to "Enable (Pure NAT)"
   - Ensure "Automatic outbound NAT for Reflection" is also enabled
   - These two settings together are required for hairpin NAT to work
2. Use split-horizon DNS / host routing — Add static routes or /etc/hosts entries so VAS nodes resolve each other via LAN IPs, but this conflicts with your requirement to use external IPs.
3. Different ListenPorts per node — Give each VAS node a unique WireGuard listen port matching the external NAT port (plane1=51841, worker1=51840, office-worker1=51842). This doesn't fix reflection but simplifies the port mapping to 1:1 which sometimes helps.
4. Manual NAT reflection rules — Add explicit OPNsense firewall rules that catch LAN-sourced traffic destined for the WAN IP and DNAT it to the correct internal host.
   I'd recommend checking option 1 first — verify the OPNsense reflection settings. Can you check in OPNsense web UI under Firewall > Settings > Advanced what the exact reflection settings are? Specifically:

- Reflection for port forwards: Enable (NAT + proxy) vs Enable (Pure NAT) vs Disable
- Automatic outbound NAT for Reflection: enabled or disabled?
  If it's set to NAT + proxy, switching to Pure NAT often fixes this for UDP traffic since the proxy mode only works with TCP.
