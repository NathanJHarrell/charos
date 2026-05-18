# jarvis-wsl network-services duplication verification

**Date:** 2026-05-02
**Investigator:** TC (read-only)
**Host:** jarvis-wsl

## TL;DR — premise correction

**There are NO duplicate host-native services on jarvis-wsl.** All three services (caddy, dnsmasq, ntfy) run *only* inside docker containers. The `ps auxf` output that suggested host-native processes is misleading: docker containers share the host PID namespace on this box, so container PIDs (`caddy run`, `ntfy serve`, `webproc … dnsmasq`) appear in the host's `ps` output as if they were native daemons. They are not.

Verification: `docker top family-caddy` returns PID 15296; `docker top family-ntfy` returns 98845; `docker top family-dns` returns 15293 — exact match to the host-visible PIDs. Host paths `/etc/caddy/`, `/var/lib/caddy/`, `/etc/ntfy/`, `/etc/dnsmasq.conf` do not exist. No `systemctl` units present for any of the three.

**Recommendation:** nothing to retire. The "duplicate" picture appears to be an artifact of how `ps` reads container processes through the shared PID namespace.

---

## caddy verdict

### Listening ports
- `:80` and `:443` (v4 and v6): bound by `docker-proxy` → forwarded to `family-caddy` container (172.19.0.6 on `family-brain_default` net).
- No host-native caddy listener on any port.

### Config canonical-source
- Host: `/etc/caddy/` does not exist; `/var/lib/caddy/` does not exist; no caddy systemd unit.
- Container `family-caddy`: `/etc/caddy/Caddyfile` present with full `*.harrell.ai` config (`scout`, `git`, `n8n`, `search`, `files`, all `tls internal`).
- The "host" PID 15296 (`caddy run --config /etc/caddy/Caddyfile`) is the container's PID 1 visible through the shared PID namespace — confirmed via `docker top family-caddy`.

### Active traffic evidence
- `curl --resolve scout.harrell.ai:443:100.75.84.100 https://scout.harrell.ai/` → HTTP 200, TLS verified (ssl_verify_result=20, internal CA).
- `curl --resolve git.harrell.ai:443:…` → HTTP/2 405 from Gitea (proxy working).
- TLS for `*.harrell.ai` is served by `family-caddy` using `tls internal` (Caddy's internal CA, no external ACME).

### Verdict
`family-caddy` (container) is the **sole** caddy. There is no host-native caddy.

### Confidence
**High.** Direct config inspection inside the container, host config dirs absent, live TLS handshake verified, `docker top` PID match.

### Risk if wrong
Killing a host-native caddy that doesn't exist costs nothing. Killing the container would take down all `*.harrell.ai` TLS termination — but that's not what the original task contemplated. **No action recommended.**

---

## dnsmasq verdict

### Listening ports
- `127.0.0.53:53` — `systemd-resolved` (unrelated stub resolver).
- `10.255.255.254:53` — listener visible in `ss` with no PID attribution (WSL2 NAT gateway address). The `family-dns` container runs in **host network mode** (`network=host`), and its `dnsmasq --no-daemon` is the actual responder bound here.
- `*:8080` — `webproc` (the dnsmasq web admin UI), also from `family-dns` container via host networking. PID 15293 → `docker top family-dns` confirms.

### Config canonical-source
- Host: `/etc/dnsmasq.conf` does not exist on host filesystem.
- Container `family-dns`: `/etc/dnsmasq.conf` contains `address=/.harrell.ai/100.75.84.100` (the tailnet IP for jarvis-wsl), `no-hosts`, `no-resolv`, `domain-needed`, `bogus-priv`.

### Active traffic evidence
- `dig @10.255.255.254 scout.harrell.ai` → `100.75.84.100` (matches container's wildcard rule). Confirms family-dns is answering.
- `dig @127.0.0.1` → connection refused (systemd-resolved on `.53`, not `.1`).

### Verdict
`family-dns` (container, host-network mode) is the **sole** dnsmasq. The host's `webproc` process visible in `ps` is the same container process. No duplicate.

### Confidence
**High** for "no host-native dnsmasq exists." **Medium** for "10.255.255.254:53 listener = family-dns" — `ss` could not show the PID because of WSL/host-net namespace quirks, but the config-and-answer match is unambiguous (only family-dns has a rule producing `100.75.84.100` for `*.harrell.ai`).

### Risk if wrong
None for retirement (nothing host-native to retire). If `family-dns` were taken down, internal `*.harrell.ai` resolution would break for any client pointing at jarvis-wsl as resolver. **No action recommended.**

---

## ntfy verdict

### Listening ports
- `0.0.0.0:8090` and `[::]:8090`: bound by `docker-proxy` → forwarded to `family-ntfy` container (port 80 inside container).
- No host-native ntfy listener.

### Config canonical-source
- Host: `/etc/ntfy/server.yml` does not exist; no ntfy systemd unit.
- Container `family-ntfy`: PID 1 = `ntfy serve` (PID 98845), confirmed via `docker top family-ntfy`. Container is on its own bridge `family-ntfy_default`.

### Active traffic evidence
- `curl http://localhost:8090/` → `HTTP/1.1 200 OK`. ntfy responding from the container via docker-proxy.

### Verdict
`family-ntfy` (container) is the **sole** ntfy. There is no host-native ntfy.

### Confidence
**High.** Same evidence pattern as caddy: host paths absent, `docker top` PID match, live response from the published port.

### Risk if wrong
Nothing host-native to retire; **no action recommended.**

---

## Cross-cutting note

If the duplication concern came from a `ps`/`htop`/audit script flagging `caddy run`, `ntfy serve`, and `webproc` as host processes — the script needs to be taught to filter container PIDs (compare against `docker top` output for each running container, or check `/proc/$pid/cgroup` for `docker` / `containerd` paths). That diagnostic-source fix will eliminate the false-positive without any service changes.
