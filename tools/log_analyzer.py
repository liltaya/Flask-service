#!/usr/bin/env python3
"""
Analyze Nginx/Apache access logs in common or combined log format.

Reports:
- HTTP status-code distribution
- Error rate (4xx + 5xx)
- Top client IPs
- Suspicious requests

Usage:
    python3 log_analyzer.py /var/log/nginx/access.log
    sudo python3 log_analyzer.py /var/log/nginx/access.log --top 20
    python3 log_analyzer.py access.log --json
"""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, TextIO
from urllib.parse import unquote


LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+'
    r'\S+\s+\S+\s+'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+|-)\s+(?P<target>\S+)(?:\s+HTTP/(?P<http_version>[^"]+))?"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<size>\d+|-)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
)

SUSPICIOUS_PATTERNS = {
    "path_traversal": re.compile(r"(?:\.\./|%2e%2e|%252e%252e)", re.I),
    "sql_injection": re.compile(
        r"(?:\bunion\b.{0,20}\bselect\b|\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|"
        r"\bdrop\s+table\b|\binformation_schema\b|sleep\s*\(|benchmark\s*\()",
        re.I,
    ),
    "xss": re.compile(
        r"(?:<script|%3cscript|javascript:|onerror\s*=|onload\s*=|document\.cookie)",
        re.I,
    ),
    "sensitive_file_probe": re.compile(
        r"(?:^|/)(?:\.env|\.git|wp-admin|wp-login\.php|phpmyadmin|server-status|"
        r"actuator|config\.json|id_rsa|passwd)(?:/|$|\?)",
        re.I,
    ),
    "command_injection": re.compile(
        r"(?:[;&|`]\s*(?:cat|wget|curl|bash|sh|nc|python|perl)\b|\$\([^)]+\))",
        re.I,
    ),
    "scanner_user_agent": re.compile(
        r"(?:sqlmap|nikto|nmap|masscan|zgrab|acunetix|nessus|dirbuster|gobuster)",
        re.I,
    ),
}

SUSPICIOUS_METHODS = {"TRACE", "CONNECT"}
ERROR_STATUSES = range(400, 600)


@dataclass(frozen=True)
class LogEntry:
    ip: str
    timestamp: str
    method: str
    target: str
    status: int
    size: int | None
    referer: str
    user_agent: str


@dataclass(frozen=True)
class SuspiciousEvent:
    line_number: int
    ip: str
    method: str
    target: str
    status: int
    reasons: tuple[str, ...]


def parse_line(line: str) -> LogEntry | None:
    match = LOG_PATTERN.match(line.rstrip("\n"))
    if not match:
        return None

    data = match.groupdict()

    try:
        ipaddress.ip_address(data["ip"])
    except ValueError:
        # Preserve proxy/hostname values, but reject empty or malformed placeholders.
        if not data["ip"] or data["ip"] == "-":
            return None

    return LogEntry(
        ip=data["ip"],
        timestamp=data["time"],
        method=data["method"],
        target=data["target"],
        status=int(data["status"]),
        size=None if data["size"] == "-" else int(data["size"]),
        referer=data.get("referer") or "",
        user_agent=data.get("user_agent") or "",
    )


def suspicious_reasons(entry: LogEntry) -> tuple[str, ...]:
    decoded_target = unquote(unquote(entry.target))
    searchable = f"{entry.target}\n{decoded_target}"
    reasons: list[str] = []

    if entry.method in SUSPICIOUS_METHODS:
        reasons.append(f"unusual_method:{entry.method}")

    for name, pattern in SUSPICIOUS_PATTERNS.items():
        value = entry.user_agent if name == "scanner_user_agent" else searchable
        if pattern.search(value):
            reasons.append(name)

    return tuple(sorted(set(reasons)))


def analyze(lines: Iterable[str], top: int) -> dict:
    status_codes: Counter[int] = Counter()
    status_classes: Counter[str] = Counter()
    ip_counts: Counter[str] = Counter()
    suspicious_by_ip: Counter[str] = Counter()
    suspicious_by_reason: Counter[str] = Counter()
    suspicious_events: list[SuspiciousEvent] = []
    malformed_lines = 0
    total_requests = 0
    error_requests = 0

    for line_number, line in enumerate(lines, start=1):
        entry = parse_line(line)
        if entry is None:
            malformed_lines += 1
            continue

        total_requests += 1
        status_codes[entry.status] += 1
        status_classes[f"{entry.status // 100}xx"] += 1
        ip_counts[entry.ip] += 1

        if entry.status in ERROR_STATUSES:
            error_requests += 1

        reasons = suspicious_reasons(entry)
        if reasons:
            suspicious_by_ip[entry.ip] += 1
            suspicious_by_reason.update(reasons)
            suspicious_events.append(
                SuspiciousEvent(
                    line_number=line_number,
                    ip=entry.ip,
                    method=entry.method,
                    target=entry.target,
                    status=entry.status,
                    reasons=reasons,
                )
            )

    error_rate = (error_requests / total_requests * 100.0) if total_requests else 0.0

    return {
        "summary": {
            "total_requests": total_requests,
            "error_requests": error_requests,
            "error_rate_percent": round(error_rate, 2),
            "malformed_lines": malformed_lines,
            "suspicious_requests": len(suspicious_events),
        },
        "status_codes": dict(sorted(status_codes.items())),
        "status_classes": dict(sorted(status_classes.items())),
        "top_ips": ip_counts.most_common(top),
        "suspicious": {
            "by_reason": suspicious_by_reason.most_common(),
            "top_ips": suspicious_by_ip.most_common(top),
            "events": [asdict(event) for event in suspicious_events[:top]],
            "events_truncated": max(0, len(suspicious_events) - top),
        },
    }


def print_text_report(report: dict) -> None:
    summary = report["summary"]

    print("=== Summary ===")
    print(f"Total requests:      {summary['total_requests']}")
    print(f"Error requests:      {summary['error_requests']}")
    print(f"Error rate:          {summary['error_rate_percent']:.2f}%")
    print(f"Malformed lines:     {summary['malformed_lines']}")
    print(f"Suspicious requests: {summary['suspicious_requests']}")

    print("\n=== Status codes ===")
    if report["status_codes"]:
        for status, count in report["status_codes"].items():
            print(f"{status}: {count}")
    else:
        print("No parsed requests")

    print("\n=== Status classes ===")
    for status_class, count in report["status_classes"].items():
        print(f"{status_class}: {count}")

    print("\n=== Top IPs ===")
    for ip, count in report["top_ips"]:
        print(f"{ip:39} {count}")

    print("\n=== Suspicious reasons ===")
    if report["suspicious"]["by_reason"]:
        for reason, count in report["suspicious"]["by_reason"]:
            print(f"{reason:30} {count}")
    else:
        print("None detected")

    print("\n=== Suspicious IPs ===")
    if report["suspicious"]["top_ips"]:
        for ip, count in report["suspicious"]["top_ips"]:
            print(f"{ip:39} {count}")
    else:
        print("None detected")

    print("\n=== Suspicious request samples ===")
    events = report["suspicious"]["events"]
    if not events:
        print("None detected")
        return

    for event in events:
        reasons = ", ".join(event["reasons"])
        print(
            f"line={event['line_number']} ip={event['ip']} "
            f"status={event['status']} method={event['method']} "
            f"reasons=[{reasons}] target={event['target']}"
        )

    truncated = report["suspicious"]["events_truncated"]
    if truncated:
        print(f"... {truncated} additional suspicious events omitted")


def write_csv_report(report: dict, stream: TextIO) -> None:
    writer = csv.writer(stream)
    writer.writerow(["section", "key", "value", "extra"])

    for key, value in report["summary"].items():
        writer.writerow(["summary", key, value, ""])

    for status, count in report["status_codes"].items():
        writer.writerow(["status_code", status, count, ""])

    for status_class, count in report["status_classes"].items():
        writer.writerow(["status_class", status_class, count, ""])

    for ip, count in report["top_ips"]:
        writer.writerow(["top_ip", ip, count, ""])

    for reason, count in report["suspicious"]["by_reason"]:
        writer.writerow(["suspicious_reason", reason, count, ""])

    for ip, count in report["suspicious"]["top_ips"]:
        writer.writerow(["suspicious_ip", ip, count, ""])

    for event in report["suspicious"]["events"]:
        writer.writerow([
            "suspicious_event",
            event["ip"],
            event["status"],
            json.dumps(
                {
                    "line_number": event["line_number"],
                    "method": event["method"],
                    "target": event["target"],
                    "reasons": event["reasons"],
                },
                ensure_ascii=False,
            ),
        ])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Nginx/Apache common or combined access logs."
    )
    parser.add_argument(
        "log_file",
        type=Path,
        help="Path to the access log, or '-' to read from stdin.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top IPs and suspicious samples to show (default: 10).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "csv"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Deprecated alias for --format json.",
    )
    return parser


def emit_report(report: dict, output_format: str, stream: TextIO) -> None:
    if output_format == "json":
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    elif output_format == "csv":
        write_csv_report(report, stream)
    else:
        old_stdout = sys.stdout
        try:
            sys.stdout = stream
            print_text_report(report)
        finally:
            sys.stdout = old_stdout


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be greater than zero")

    output_format = "json" if args.json else args.format

    try:
        if str(args.log_file) == "-":
            report = analyze(sys.stdin, args.top)
        else:
            with args.log_file.open("r", encoding="utf-8", errors="replace") as handle:
                report = analyze(handle, args.top)
    except FileNotFoundError:
        print(f"error: file not found: {args.log_file}", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"error: permission denied: {args.log_file}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: cannot read {args.log_file}: {exc}", file=sys.stderr)
        return 2

    try:
        if args.output:
            with args.output.open("w", encoding="utf-8", newline="") as stream:
                emit_report(report, output_format, stream)
        else:
            emit_report(report, output_format, sys.stdout)
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
