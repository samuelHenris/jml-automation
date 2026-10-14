# JML Automation

HR-driven **Joiner / Mover / Leaver** identity lifecycle automation in Python.
HR is the source of truth. Access follows HR data automatically, with a dry-run
mode, a safety guard, and an audit trail.

## Problem

Manual account management causes two classic failures: new hires wait days for
access, and people who move or leave **keep access they should no longer have**
(privilege creep, orphaned accounts). Most IAM audit findings come from the
mover and leaver steps.

## How it works

```
HR feed (CSV)
     |
     v
 Diff engine ---- compares HR state vs directory state
     |            -> JOINER / MOVER / LEAVER / REHIRE / SYNC / ORPHAN
     v
 Policy (YAML) -- department + title -> groups
     |
     v
 Safety guard --- aborts if too many accounts would be disabled
     |
     v
 Connector ------ mock JSON directory now; LDAP and Entra ID next
     |
     v
 Audit log ------ append-only JSONL, dry-run included
```

| Event | Trigger | Action |
|---|---|---|
| Joiner | In HR, no account | Create account, assign groups from policy |
| Mover | Department/title changed | Add new groups **and remove old ones** |
| Leaver | Terminated and end date reached | Disable account, strip all groups |
| Rehire | Active in HR, account disabled | Re-enable, re-sync groups |
| Sync | Group drift or policy change | Correct to match policy |
| Orphan | Enabled account, no HR record | **Flag only**, never auto-changed |

## Quick start

```bash
pip install -e ".[dev]"

# Dry-run is the default: shows what WOULD change
jml sync --hr data/hr_sample.csv

# Make the changes
jml sync --hr data/hr_sample.csv --apply

# "Day 2": one joiner, one mover, one leaver, one scheduled leaver
jml sync --hr data/hr_sample_day2.csv --apply
```

Example day-2 output:

```
[MOVER ] E1003 sofia.virtanen  +fin-all +fin-reporting -dev-tools -eng-all -github-users (Engineering/Software Engineer -> Finance/Financial Analyst)
[LEAVER] E1005 elina.makinen   -all-staff -hr-all -hris-access (end_date 2026-10-09)
[JOINER] E1011 noora.hakala    +all-staff +dev-tools +eng-all +github-users
```

Run it again and it reports `No changes needed` (idempotent).

## Design decisions

- **Dry-run by default.** Changes need an explicit `--apply`.
- **Idempotent.** The diff is a pure function; a reconciled directory yields zero actions.
- **Access is data.** Role mapping lives in `config/roles.yaml`, not in code.
- **Least privilege by default.** Unknown departments and titles get only default groups.
- **Managed groups only.** The tool never removes groups that are not in the policy file.
- **Safety guard.** A run that would disable more than 20% of enabled accounts aborts
  (`--max-leavers-pct`). An empty HR feed is rejected outright.
- **Scheduled leavers.** A future end date is not disabled until it arrives.
- **Audit trail.** Every planned or applied action is logged with timestamp, run id, and mode.

## Threat model (short)

| Risk | Mitigation |
|---|---|
| Corrupt or truncated HR feed disables everyone | Empty-feed rejection, leaver percentage guard, dry-run first |
| Privilege creep after role change | Mover logic removes old managed groups |
| Orphaned accounts | Orphan detection flags accounts HR does not know |
| Tool strips legitimate manual grants | Only policy-managed groups are removable |
| Credentials in the repo | `.env` git-ignored, `.env.example` only, gitleaks in CI |
| No accountability for changes | Append-only audit log |

**Production hardening (not in this repo):** signed or authenticated HR feed,
approval step for leavers above a threshold, immutable log storage, session and
token revocation on leave, manager notification.

## Framework mapping

| Control | Where it shows up |
|---|---|
| NIST 800-53 AC-2 (Account Management), PS-4 (Termination), PS-5 (Transfer) | Joiner / Leaver / Mover logic |
| NIST 800-53 AC-6 (Least Privilege) | Policy-driven groups, least-privilege defaults |
| NIST 800-53 AU-2 / AU-12 (Audit) | `audit.py` |
| ISO 27001:2022 A.5.16, A.5.18, A.6.5 | Identity management, access rights, change/termination of employment |
| CIS Controls v8 5 and 6 | Account management, access control management |

## Roadmap

- [ ] OpenLDAP connector (Docker Compose) alongside the mock
- [ ] Microsoft Entra ID connector via Graph API
- [ ] Access review report (stale accounts, over-privileged users)
- [ ] Notification hook for leavers

## Development

```bash
pytest -q
ruff check .
```
