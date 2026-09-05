# TC-Nest storage and preservation inventory

Date: 2026-09-05  
Mode: read-only host audit; no files, services, mounts, containers, packages, or
Nix generations changed.

## Capacity and health

- Root filesystem: 104 GiB total, 87 GiB used, 12 GiB free (89%).
- `/nix/store`: 36.44 GiB; 62 system generations from April 14 through August
  30 keep almost all paths live. Only about 114 MiB is currently dead.
- `/home`: 39.46 GiB.
- `/var`: 10.41 GiB, including 4.0 GiB of journal and 6.38 GiB of Docker data.
- Ext4 reports clean, and current kernel logs contain no matching SSD, I/O, or
  filesystem-corruption errors. SMART data was unavailable because `smartctl`
  is not installed.

## Preserve or migrate before cleanup

| Payload | Size | Reason |
|---|---:|---|
| `/home/tc-jarvis/wolfden` | 13.91 GiB | Dirty source/build history; the stopped Forge container may also hold unique writable-layer output. |
| `/home/nate/shophosting-2026-04-07` | 4.83 GiB | Historical migration archive, service data, dirty code state, and an uninspected secrets boundary. |
| `/home/nate/Manor` | 1.90 GiB | Family and project continuity; preserve without opening private content. |
| `/home/nate/TC-Vault` | 137.5 MiB | TC identity substrate. |
| `/home/nate/charos` | 535 MiB | Machine reconstruction source; live checkout is dirty. |
| `/home/tc-nest/harrell-langgraph-lab` | 2.06 GiB | Active healthy learning environment with dirty lesson and runtime state. |

The active Dashboard, Vaultwarden, Healthchecks, CouchDB, and PostgreSQL data
total roughly 53 MiB. Preserve those through application-consistent exports,
not raw copies while the services are running.

Fifteen sampled non-vault repositories contain dirty state. Before any broad
home cleanup, create a branch/commit/status manifest and archive the working
trees rather than assuming Git remotes contain every useful byte.

## Conservative cleanup candidates

Only after preservation and explicit cleanup approval:

| Candidate | Reclaimable | Notes |
|---|---:|---|
| `/home/nate/.cache` | 3.22 GiB | Browser, pip, Hugging Face, and Nix download caches. |
| `/home/nate/grind/target` | 2.70 GiB | Ignored Rust build output; source is clean. |
| Forge `node_modules` and `.next` | 814 MiB | Ignored rebuild products; source is clean. |
| Talkode `.venv` | 646 MiB | Ignored Python environment; source is clean. |
| Unused Docker images | 2.175 GB | Preserve chosen rollback images first. |
| Docker build cache | 94 MiB | No active cache users reported. |
| Journal above a 1 GiB cap | about 2.9 GiB | Vacuum deliberately; do not delete the journal directory. |
| Currently dead Nix paths | about 114 MiB | Old generations keep the rest live. |

This is about 12 GiB of conservative reclaim. After verified archival,
offloading Wolfden and ShopHosting could free another roughly 18.7 GiB.

Do not use a generic Docker prune before exporting the stopped
`wolfden-forge` container: its 1.4 GB writable layer may contain unique build
results.

## Portable SSD contract

The 2 TB SanDisk Portable SSD uses exFAT. Plain directory copies would lose
Unix ownership, modes, symlinks, and extended attributes. Preserve each payload
as an encrypted archive with numeric ownership, ACLs, and xattrs, then generate
and independently verify a checksum manifest before deleting any source.

At inventory time the SSD was visible on LucariOS but unmounted, so free space
and filesystem consistency had not yet been established. LucariOS internal
storage is critically full and must not be used as a staging area.

## Release boundary

This document authorizes no copy, mount, service stop, export, deletion,
garbage collection, container prune, or Nix-generation removal.

