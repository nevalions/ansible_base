# wg_cidr_guard role

Deploy a systemd-based guard that checks WireGuard runtime `AllowedIPs` for a required CIDR and restarts
`wg-quick@<interface>` when the CIDR is missing.

## What it deploys

- Guard script: `{{ wg_cidr_guard_script_path }}`
- Service unit: `{{ wg_cidr_guard_service_unit }}` (oneshot)
- Timer unit: `{{ wg_cidr_guard_timer_unit }}`

The timer runs every `wg_cidr_guard_check_interval` and also after boot delay
`wg_cidr_guard_check_on_boot_delay`.

## Default behavior

- Interface: `wg99`
- Required CIDR: `[metallb-vip-cidr]`
- On missing CIDR: restart `wg-quick@wg99.service`
- Uses `flock` lock file at `/run/wg-cidr-guard.lock` to prevent overlap

## Variables

- `wg_cidr_guard_operation`: `install`, `remove`, `verify`
- `wg_cidr_guard_interface`
- `wg_cidr_guard_required_cidr`
- `wg_cidr_guard_check_interval`
- `wg_cidr_guard_check_on_boot_delay`
- `wg_cidr_guard_script_path`
- `wg_cidr_guard_run_on_install`

## Playbooks

- `wg_cidr_guard_manage.yaml`
- `wg_cidr_guard_verify.yaml`
- `wg_cidr_guard_remove.yaml`

## Example

```bash
ansible-playbook -i hosts_bay.ini wg_cidr_guard_manage.yaml
ansible-playbook -i hosts_bay.ini wg_cidr_guard_verify.yaml
```
