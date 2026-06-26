#!/usr/bin/env python3
"""
AgenticOS Docker Hardening Auditor

Safe by default. This script does NOT edit docker-compose files, restart containers,
change firewall rules, or expose services. It inventories compose files and running
Docker ports, then writes Markdown reports and patch suggestions to Obsidian.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
SKIP_DIR_NAMES = {
    ".git", ".cache", "node_modules", "venv", ".venv", "__pycache__",
    "pgdata", "postgres", "postgres-data", "db_data", "database", "redis-data",
    "cache", "logs", "backups", "backup", "Photos", "photos", "library", "upload",
}

LAN_LIKELY_KEYWORDS = [
    "homepage", "homarr", "dashy", "heimdall", "immich", "syncthing",
    "jellyfin", "plex", "navidrome", "nextcloud", "vaultwarden",
]
PRIVATE_LIKELY_KEYWORDS = [
    "postgres", "postgresql", "mariadb", "mysql", "redis", "meili", "meilisearch",
    "qdrant", "ollama", "openclaw", "searx", "searxng", "adminer", "pgadmin",
    "n8n", "linkwarden", "worker", "db", "database", "machine_learning",
]

@dataclass
class PortMapping:
    compose_file: str
    service: str
    raw: str
    host_ip: str
    host_port: str
    container_port: str
    protocol: str
    exposure: str
    line_no: int
    suggestion: str
    category: str

@dataclass
class VolumeMapping:
    compose_file: str
    service: str
    raw: str
    host_path: str
    container_path: str
    line_no: int

@dataclass
class ComposeInfo:
    path: str
    services: List[str]
    ports: List[PortMapping]
    volumes: List[VolumeMapping]
    validation_status: str
    validation_output: str

@dataclass
class DockerContainer:
    name: str
    image: str
    status: str
    ports: str
    exposure: str


def run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 12) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"Timed out running: {' '.join(cmd)}"
    except Exception as e:
        return 1, f"Error running {' '.join(cmd)}: {e}"


def uncomment(line: str) -> str:
    # crude but good enough for compose short syntax; avoids stripping hashes inside quotes only partially
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def strip_quotes(s: str) -> str:
    s = s.strip().rstrip(",")
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1].strip()
    return s


def service_category(name: str) -> str:
    low = name.lower()
    if any(k in low for k in LAN_LIKELY_KEYWORDS):
        return "probably LAN-needed"
    if any(k in low for k in PRIVATE_LIKELY_KEYWORDS):
        return "probably private"
    return "review manually"


def classify_host_ip(host_ip: str) -> str:
    h = host_ip.strip().lower()
    if h in {"127.0.0.1", "localhost", "::1", "[::1]"}:
        return "LOOPBACK_ONLY"
    if h in {"", "0.0.0.0", "::", "[::]"}:
        return "LAN_EXPOSED"
    return "SPECIFIC_INTERFACE"


def parse_short_port(raw: str) -> Optional[Tuple[str, str, str, str]]:
    raw = strip_quotes(raw.strip())
    if not raw:
        return None
    # long syntax line like target: is not short syntax
    if re.match(r"^(target|published|host_ip|protocol)\s*:", raw):
        return None
    proto = "tcp"
    if "/" in raw:
        raw, proto = raw.rsplit("/", 1)
    raw = raw.strip()
    # skip container-only expose like "8080"
    if ":" not in raw:
        return None
    # bracket IPv6: [::1]:8080:80
    if raw.startswith("["):
        m = re.match(r"^(\[[^\]]+\]):(\d+):(\d+)$", raw)
        if m:
            return m.group(1), m.group(2), m.group(3), proto
    parts = raw.split(":")
    if len(parts) == 2:
        return "", parts[0], parts[1], proto
    if len(parts) >= 3:
        # join to tolerate unbracketed IPv6-ish forms, though compose usually brackets them
        return ":".join(parts[:-2]), parts[-2], parts[-1], proto
    return None


def parse_volume(raw: str) -> Optional[Tuple[str, str]]:
    raw = strip_quotes(raw.strip())
    if not raw or raw.startswith("type:"):
        return None
    # Skip named-only volumes
    if ":" not in raw:
        return None
    parts = raw.split(":")
    if len(parts) < 2:
        return None
    host = parts[0]
    dest = parts[1]
    # Ignore pure docker named volumes unless they look path-ish
    if not (host.startswith("/") or host.startswith(".") or host.startswith("~")):
        return None
    return host, dest


def replacement_suggestion(raw: str, category: str) -> str:
    parsed = parse_short_port(raw)
    if not parsed:
        return "Review long syntax manually; set host_ip: 127.0.0.1 if private."
    host_ip, host_port, container_port, proto = parsed
    if classify_host_ip(host_ip) == "LOOPBACK_ONLY":
        return "Already loopback-only."
    if category == "probably LAN-needed":
        return "May need LAN access. Keep exposed only if you actually use it from phone/LAN, or put behind Tailscale/reverse proxy."
    suffix = f"/{proto}" if proto and proto != "tcp" else ""
    return f"Consider changing to: 127.0.0.1:{host_port}:{container_port}{suffix}"


def parse_compose(path: Path) -> ComposeInfo:
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    services_indent: Optional[int] = None
    current_service: Optional[str] = None
    service_indent: Optional[int] = None
    in_ports = False
    in_volumes = False
    ports_indent: Optional[int] = None
    vols_indent: Optional[int] = None
    services: List[str] = []
    ports: List[PortMapping] = []
    volumes: List[VolumeMapping] = []
    long_port: Optional[Dict[str, str]] = None
    long_port_line = 0

    def finish_long_port() -> None:
        nonlocal long_port, long_port_line
        if not long_port or not current_service:
            long_port = None
            return
        target = long_port.get("target", "")
        published = long_port.get("published", "")
        if not target or not published:
            long_port = None
            return
        host_ip = long_port.get("host_ip", "")
        proto = long_port.get("protocol", "tcp")
        raw = f"host_ip={host_ip or '*'} published={published} target={target}/{proto}"
        exposure = classify_host_ip(host_ip)
        cat = service_category(current_service)
        suggestion = "Already loopback-only." if exposure == "LOOPBACK_ONLY" else (
            "May need LAN access. Keep exposed only if needed or place behind controlled entry point."
            if cat == "probably LAN-needed" else
            f"Consider long syntax host_ip: 127.0.0.1 for published port {published}."
        )
        ports.append(PortMapping(str(path), current_service, raw, host_ip, published, target, proto,
                                 exposure, long_port_line, suggestion, cat))
        long_port = None

    for idx, rawline in enumerate(lines, 1):
        no_comment = uncomment(rawline.rstrip("\n"))
        if not no_comment.strip():
            continue
        indent = len(no_comment) - len(no_comment.lstrip(" "))
        stripped = no_comment.strip()

        if stripped == "services:":
            services_indent = indent
            current_service = None
            continue

        if services_indent is None:
            continue

        # exit services if we hit another top-level block
        if indent <= services_indent and stripped and not stripped.startswith("-") and stripped != "services:":
            finish_long_port()
            current_service = None
            in_ports = False
            in_volumes = False
            continue

        # service key at one level below services:
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*(?:#.*)?$", stripped)
        if m and indent > services_indent and (service_indent is None or indent <= service_indent):
            finish_long_port()
            current_service = m.group(1)
            service_indent = indent
            in_ports = False
            in_volumes = False
            ports_indent = None
            vols_indent = None
            if current_service not in services:
                services.append(current_service)
            continue

        if not current_service:
            continue

        if stripped.startswith("ports:"):
            finish_long_port()
            in_ports = True
            in_volumes = False
            ports_indent = indent
            continue
        if stripped.startswith("volumes:"):
            finish_long_port()
            in_volumes = True
            in_ports = False
            vols_indent = indent
            continue

        if in_ports and ports_indent is not None and indent <= ports_indent and not stripped.startswith("-"):
            finish_long_port()
            in_ports = False
        if in_volumes and vols_indent is not None and indent <= vols_indent and not stripped.startswith("-"):
            in_volumes = False

        if in_ports:
            if stripped.startswith("- "):
                finish_long_port()
                val = stripped[2:].strip()
                if val.startswith("target:"):
                    long_port = {}
                    long_port_line = idx
                    key, v = val.split(":", 1)
                    long_port[key.strip()] = strip_quotes(v.strip())
                    continue
                parsed = parse_short_port(val)
                if parsed:
                    host_ip, host_port, container_port, proto = parsed
                    exposure = classify_host_ip(host_ip)
                    cat = service_category(current_service)
                    ports.append(PortMapping(str(path), current_service, strip_quotes(val), host_ip, host_port,
                                             container_port, proto, exposure, idx,
                                             replacement_suggestion(val, cat), cat))
            elif long_port and ":" in stripped:
                key, v = stripped.split(":", 1)
                key = key.strip()
                if key in {"target", "published", "host_ip", "protocol"}:
                    long_port[key] = strip_quotes(v.strip())

        if in_volumes:
            if stripped.startswith("- "):
                val = stripped[2:].strip()
                parsed_vol = parse_volume(val)
                if parsed_vol:
                    host, dest = parsed_vol
                    volumes.append(VolumeMapping(str(path), current_service, strip_quotes(val), host, dest, idx))

    finish_long_port()

    # validate with docker compose if available; this can fail due missing env and that is okay to report
    rc, out = run(["docker", "compose", "-f", str(path), "config", "--quiet"], cwd=path.parent, timeout=15)
    if rc == 0:
        validation_status = "ok"
        validation_output = "docker compose config --quiet passed"
    elif rc == 127:
        validation_status = "not checked"
        validation_output = out
    else:
        validation_status = "warning"
        validation_output = out[:1200]

    return ComposeInfo(str(path), services, ports, volumes, validation_status, validation_output)


def should_skip_dir(p: Path) -> bool:
    return p.name in SKIP_DIR_NAMES or p.name.startswith(".") and p.name not in {".config"}


def find_compose_files(roots: Iterable[Path]) -> List[Path]:
    found: List[Path] = []
    seen = set()
    for root in roots:
        root = root.expanduser()
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dpath = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not should_skip_dir(dpath / d)]
            for fn in filenames:
                if fn in COMPOSE_NAMES:
                    p = dpath / fn
                    rp = str(p.resolve())
                    if rp not in seen:
                        seen.add(rp)
                        found.append(p)
    return sorted(found)


def docker_containers() -> List[DockerContainer]:
    rc, out = run(["docker", "ps", "--format", "{{json .}}"], timeout=10)
    if rc != 0:
        return [DockerContainer("docker unavailable", "", out, "", "UNKNOWN")]
    containers: List[DockerContainer] = []
    for line in out.splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        name = obj.get("Names", "")
        image = obj.get("Image", "")
        status = obj.get("Status", "")
        ports = obj.get("Ports", "")
        if "0.0.0.0:" in ports or ":::" in ports:
            exposure = "LAN_EXPOSED"
        elif "127.0.0.1:" in ports or "[::1]:" in ports:
            exposure = "LOOPBACK_ONLY"
        elif ports:
            exposure = "REVIEW"
        else:
            exposure = "NO_PUBLISHED_PORTS"
        containers.append(DockerContainer(name, image, status, ports, exposure))
    return containers


def md_table(headers: List[str], rows: List[List[str]]) -> str:
    def cell(x: object) -> str:
        return str(x).replace("\n", "<br>").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(cell(x) for x in row) + " |")
    return "\n".join(out)


def relpath(p: str) -> str:
    try:
        return str(Path(p).expanduser())
    except Exception:
        return p


def write_reports(vault: Path, infos: List[ComposeInfo], containers: List[DockerContainer], roots: List[Path]) -> Tuple[Path, Path, Path]:
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    date = now.strftime("%Y-%m-%d")
    base = vault.expanduser() / "Agentic OS"
    hardening_dir = base / "Docker Hardening Reports"
    map_dir = base
    plan_dir = base / "Patch Plans"
    hardening_dir.mkdir(parents=True, exist_ok=True)
    plan_dir.mkdir(parents=True, exist_ok=True)

    all_ports = [p for info in infos for p in info.ports]
    exposed = [p for p in all_ports if p.exposure == "LAN_EXPOSED"]
    private_exposed = [p for p in exposed if p.category == "probably private"]
    lan_exposed = [p for p in exposed if p.category == "probably LAN-needed"]
    review_exposed = [p for p in exposed if p.category == "review manually"]
    all_vols = [v for info in infos for v in info.volumes]

    report_path = hardening_dir / f"{stamp} Docker Hardening Audit.md"
    map_path = map_dir / "Self-Hosted Services Map.md"
    plan_path = plan_dir / f"{stamp} Docker Hardening Patch Plan.md"

    report = []
    report.append(f"# Docker Hardening Audit - {date}")
    report.append("")
    report.append("Safe by default: this report did not edit compose files, restart containers, change firewall rules, or expose services.")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append(md_table(["Item", "Count"], [
        ["Compose files found", len(infos)],
        ["Services discovered in compose", sum(len(i.services) for i in infos)],
        ["Published ports found in compose", len(all_ports)],
        ["LAN-exposed compose ports", len(exposed)],
        ["Probably-private LAN exposures", len(private_exposed)],
        ["Running Docker containers", len([c for c in containers if c.name != "docker unavailable"])],
    ]))
    report.append("")
    report.append("## Scan roots")
    report.append("")
    for r in roots:
        report.append(f"- `{r.expanduser()}`")
    report.append("")
    report.append("## Running Docker containers")
    report.append("")
    report.append(md_table(["Container", "Image", "Status", "Ports", "Exposure"],
                           [[c.name, c.image, c.status, c.ports or "-", c.exposure] for c in containers]))
    report.append("")
    report.append("## Compose files")
    report.append("")
    report.append(md_table(["Compose file", "Services", "Validation"],
                           [[i.path, ", ".join(i.services) or "-", i.validation_status] for i in infos]))
    report.append("")
    validation_warnings = [i for i in infos if i.validation_status == "warning"]
    if validation_warnings:
        report.append("## Compose validation warnings")
        report.append("")
        for i in validation_warnings:
            report.append(f"### `{i.path}`")
            report.append("")
            report.append("```text")
            report.append(i.validation_output or "No output")
            report.append("```")
            report.append("")

    report.append("## LAN-exposed compose ports")
    report.append("")
    if exposed:
        report.append(md_table(["Service", "Host", "Container", "Category", "Compose file", "Line", "Suggestion"],
                               [[p.service, f"{p.host_ip or '0.0.0.0'}:{p.host_port}", f"{p.container_port}/{p.protocol}", p.category, p.compose_file, p.line_no, p.suggestion] for p in exposed]))
    else:
        report.append("No LAN-exposed compose ports were detected in parsed compose files.")
    report.append("")

    report.append("## Loopback-only compose ports")
    report.append("")
    loopback = [p for p in all_ports if p.exposure == "LOOPBACK_ONLY"]
    if loopback:
        report.append(md_table(["Service", "Host", "Container", "Compose file", "Line"],
                               [[p.service, f"{p.host_ip}:{p.host_port}", f"{p.container_port}/{p.protocol}", p.compose_file, p.line_no] for p in loopback]))
    else:
        report.append("No loopback-only compose ports were detected in parsed compose files.")
    report.append("")

    report.append("## Data locations discovered from volume mounts")
    report.append("")
    if all_vols:
        report.append(md_table(["Service", "Host path", "Container path", "Compose file", "Line"],
                               [[v.service, v.host_path, v.container_path, v.compose_file, v.line_no] for v in all_vols]))
    else:
        report.append("No host-path volume mounts were detected by the simple parser.")
    report.append("")

    report.append("## Suggested controlled hardening flow")
    report.append("")
    report.append("1. Pick one stack only.")
    report.append("2. Decide whether each exposed port truly needs LAN access.")
    report.append("3. For private apps, change `PORT:CONTAINER` or `0.0.0.0:PORT:CONTAINER` to `127.0.0.1:PORT:CONTAINER`.")
    report.append("4. Run `docker compose config` in that stack folder.")
    report.append("5. Run `docker compose up -d` for that stack only.")
    report.append("6. Verify the app still works locally.")
    report.append("7. Only after local hardening, put truly external services behind Tailscale, reverse proxy auth, or another single controlled entry point.")
    report.append("")

    report_path.write_text("\n".join(report), encoding="utf-8")

    # Self-hosted services map, overwrite latest intentionally
    map_rows = []
    by_service: Dict[Tuple[str, str], Dict[str, object]] = {}
    for info in infos:
        for svc in info.services:
            by_service[(info.path, svc)] = {"ports": [], "vols": []}
        for p in info.ports:
            by_service.setdefault((p.compose_file, p.service), {"ports": [], "vols": []})["ports"].append(p)
        for v in info.volumes:
            by_service.setdefault((v.compose_file, v.service), {"ports": [], "vols": []})["vols"].append(v)
    for (compose, svc), data in sorted(by_service.items()):
        ports = data["ports"]  # type: ignore
        vols = data["vols"]  # type: ignore
        urls = []
        exposures = []
        for p in ports:
            host = "127.0.0.1" if p.exposure == "LOOPBACK_ONLY" else (p.host_ip or "LAN IP")
            scheme = "http"
            urls.append(f"{scheme}://{host}:{p.host_port}")
            exposures.append(p.exposure)
        exposure_level = "NO_PUBLISHED_PORTS" if not exposures else ", ".join(sorted(set(exposures)))
        map_rows.append([
            svc,
            ", ".join(urls) if urls else "-",
            exposure_level,
            "; ".join(v.host_path for v in vols) if vols else "-",
            "unknown / check manually",
            compose,
        ])
    map_md = []
    map_md.append("# Self-Hosted Services Map")
    map_md.append("")
    map_md.append(f"Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    map_md.append("")
    map_md.append("This is an automatically generated map from Docker compose files. Backup status is marked unknown until you verify it.")
    map_md.append("")
    map_md.append(md_table(["Service", "Likely URL", "Exposure", "Data location", "Backup status", "Compose file"], map_rows))
    map_md.append("")
    map_md.append("## Exposure legend")
    map_md.append("")
    map_md.append("- `LOOPBACK_ONLY`: bound to 127.0.0.1, safest for private local apps.")
    map_md.append("- `LAN_EXPOSED`: bound to 0.0.0.0/all interfaces, reachable from other devices on your network.")
    map_md.append("- `SPECIFIC_INTERFACE`: bound to a specific IP/interface; review manually.")
    map_md.append("- `NO_PUBLISHED_PORTS`: no host port detected.")
    map_path.write_text("\n".join(map_md), encoding="utf-8")

    # Patch plan
    plan = []
    plan.append(f"# Docker Hardening Patch Plan - {date}")
    plan.append("")
    plan.append("This is a review plan only. It does not apply edits. Apply one stack at a time after reading the compose file.")
    plan.append("")
    plan.append("## Highest priority candidates")
    plan.append("")
    candidates = private_exposed + review_exposed
    if candidates:
        plan.append(md_table(["Priority", "Service", "Current", "Suggested change", "Compose file", "Line"],
                             [["High" if p.category == "probably private" else "Review", p.service, p.raw, p.suggestion, p.compose_file, p.line_no] for p in candidates]))
    else:
        plan.append("No obvious private LAN-exposed compose ports were detected.")
    plan.append("")
    plan.append("## Probably LAN-needed services")
    plan.append("")
    if lan_exposed:
        plan.append(md_table(["Service", "Current", "Reason", "Compose file", "Line"],
                             [[p.service, p.raw, "Name suggests this may be used from phone/LAN. Confirm manually.", p.compose_file, p.line_no] for p in lan_exposed]))
    else:
        plan.append("No likely LAN-needed services were detected as LAN-exposed by name.")
    plan.append("")
    plan.append("## Safe manual procedure")
    plan.append("")
    plan.append("```bash")
    plan.append("# 1. Go to one stack folder")
    plan.append("cd /path/to/one/compose/folder")
    plan.append("")
    plan.append("# 2. Back up compose file")
    plan.append("cp docker-compose.yml docker-compose.yml.backup.$(date +%s)")
    plan.append("")
    plan.append("# 3. Edit only one service port binding")
    plan.append("xed docker-compose.yml")
    plan.append("")
    plan.append("# 4. Validate")
    plan.append("docker compose config")
    plan.append("")
    plan.append("# 5. Restart only this stack")
    plan.append("docker compose up -d")
    plan.append("")
    plan.append("# 6. Verify")
    plan.append("docker ps --format 'table {{.Names}}\\t{{.Ports}}'")
    plan.append("```")
    plan_path.write_text("\n".join(plan), encoding="utf-8")

    # JSON raw data for AI or future use
    raw_path = hardening_dir / f"{stamp} Docker Hardening Audit.json"
    raw_obj = {
        "generated_at": now.isoformat(),
        "roots": [str(r.expanduser()) for r in roots],
        "compose_files": [asdict(i) for i in infos],
        "containers": [asdict(c) for c in containers],
    }
    raw_path.write_text(json.dumps(raw_obj, indent=2), encoding="utf-8")

    return report_path, map_path, plan_path


def main() -> int:
    parser = argparse.ArgumentParser(description="AgenticOS Docker hardening audit and self-hosted services map generator")
    parser.add_argument("--root", action="append", help="Root folder to scan. Can be repeated. Defaults to ~/docker and ~/selfhosted.")
    parser.add_argument("--vault", default=os.environ.get("OBSIDIAN_VAULT", "~/vault"), help="Obsidian vault path")
    parser.add_argument("--include-home", action="store_true", help="Also scan your whole home folder. Slower; skips common data folders.")
    args = parser.parse_args()

    roots = [Path(r) for r in args.root] if args.root else [Path("~/docker"), Path("~/selfhosted")]
    if args.include_home:
        roots.append(Path("~"))
    # de-dupe existing-ish roots
    deduped: List[Path] = []
    seen = set()
    for r in roots:
        s = str(r.expanduser())
        if s not in seen:
            seen.add(s)
            deduped.append(r)
    roots = deduped

    compose_files = find_compose_files(roots)
    infos = [parse_compose(p) for p in compose_files]
    containers = docker_containers()
    report, service_map, patch_plan = write_reports(Path(args.vault), infos, containers, roots)

    print("AgenticOS Docker hardening audit complete.")
    print(f"Compose files found: {len(infos)}")
    print(f"Report: {report}")
    print(f"Services map: {service_map}")
    print(f"Patch plan: {patch_plan}")
    print("")
    print("Nothing was edited or restarted.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
