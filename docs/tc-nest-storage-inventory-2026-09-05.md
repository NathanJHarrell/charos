# TC-Nest storage and preservation inventory

Date: 2026-09-05  
Initial mode: read-only host audit. The later preservation execution is recorded
below; no source cleanup or NixOS activation has occurred.

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
Unix ownership, modes, symlinks, and extended attributes. Preserve the selected
payloads inside a LUKS2 container file with an ext4 filesystem, leaving the
existing exFAT partition and its 487 GB of data unchanged. The recommended
initial container size is 128 GiB for roughly 25 GiB of current preservation
material plus future verified snapshots.

Store a newly generated LUKS passphrase in Vaultwarden before formatting the
container. Back up the LUKS header separately, checksum both the container and
header, close and reopen the mapping, run an ext4 check, and restore a canary
before any source cleanup. Never place the passphrase, Vaultwarden session, or
decrypted secret content in logs or transcripts.

At inventory time the SSD was attached directly to TC-Nest and unmounted. It
had roughly 1.4 TB free and no attach-time kernel errors. LucariOS internal
storage is critically full and was not used as a staging area.

## Preservation execution

The existing exFAT filesystem and its approximately 487 GB of prior content
were left intact. A fully allocated 128 GiB file named
`TC-Nest-Preservation/tc-nest-preservation-2026-09-05.luks` now contains a
LUKS2 mapping and ext4 filesystem labeled `TC-Nest-Preserve`. Its newly
generated key is stored in Vaultwarden. The LUKS header was copied separately
to TC's persistent Cove-backed home and checksummed.

Before data transfer, the vault passed all of these recovery gates:

- close the mapper and confirm `/dev/mapper/tc-nest-preserve` disappeared;
- retrieve the key from Vaultwarden and reopen it without a plaintext key file;
- run a clean read-only `e2fsck`;
- remount the filesystem and verify the README and canary SHA-256 hashes.

The preservation set includes the full dirty Wolfden tree; Nathan's home with
only named rebuildable caches excluded; the LangGraph learning lab; TC's and
the historical family accounts' continuity state; and machine reconstruction
metadata. Live PostgreSQL, Vaultwarden, Healthchecks, Dashboard, and CouchDB
state was captured through logical, SQLite-online, validated JSON, or bounded
quiesced exports as appropriate. The stopped `wolfden-forge` container was
committed and saved as a gzip-compressed Docker archive; both gzip/tar parsing
and its stored SHA-256 passed. The active LangGraph tree's paused checksum pass
reported zero differences, and the service returned to running state.

The final destination manifest contains 788,354 regular-file SHA-256 records,
955,472 total filesystem entries, and 32,068,343,137 bytes. A checksum-mode
comparison found no difference in Wolfden. Every inventoried dirty repository
has the same source and destination HEAD and dirty-entry count. Four expected
live-churn paths changed after the point-in-time copy: Syncthing's rebuildable
SQLite WAL and shared-memory files, the append-only panic log, and the generated
family-bus latest-message view. Their exact paths are retained in the encrypted
comparison log; none is part of the proposed cleanup set.

## Release boundary

Preservation writes and bounded export pauses were explicitly authorized and
are complete. Nathan subsequently authorized and completed the named
rebuildable-file cleanup, journal vacuum, stopped Wolfden container/image
removal, dangling-image and build-cache cleanup, and removal of NixOS
generations 1 through 61. Generation 62 remains the 25.11 rollback and
generation 63 is the verified live 26.05 system. The boot menu contains only
those two generations.

Nathan then explicitly authorized deletion of the internal-disk Wolfden and
ShopHosting trees if their encrypted SSD copies were confirmed. The vault was
reopened read-only and both exact source/destination pairs were checked again.
Wolfden matched at 606,077 regular files and 48,920 symlinks; ShopHosting
matched at 4,633 regular files and 2 symlinks. Checksum-mode rsync reported no
content differences after excluding only regenerated `.git/index` caches and
directory timestamps. Both repositories separately matched on HEAD, staged
file map, and complete dirty-state fingerprint. TC then removed only
`/home/tc-jarvis/wolfden` and `/home/nate/shophosting-2026-04-07`, reclaiming
20,113,276,928 allocated bytes. Root availability rose to 41,357,901,824 bytes
(39% free); all six retained containers remained up and zero systemd units
failed. The SSD was cleanly unmounted and its LUKS mapper closed. Nathan states
these Jarvis-originated trees also exist in B2/restic; that remote backup was
not independently audited during this refresh.
