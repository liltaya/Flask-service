from io import StringIO

from tools.log_analyzer import analyze, parse_line, suspicious_reasons, write_csv_report


def line(ip="127.0.0.1", method="GET", target="/", status=200, ua="curl/8.5.0"):
    return (
        f'{ip} - - [29/Jul/2026:17:10:41 -0700] '
        f'"{method} {target} HTTP/1.1" {status} 42 "-" "{ua}"\n'
    )


def test_parse_combined_log_line():
    entry = parse_line(line(target="/health", status=200))
    assert entry is not None
    assert entry.ip == "127.0.0.1"
    assert entry.target == "/health"
    assert entry.status == 200


def test_status_codes_and_error_rate():
    report = analyze([line(status=200), line(status=404), line(status=500)], top=10)
    assert report["summary"]["total_requests"] == 3
    assert report["summary"]["error_requests"] == 2
    assert report["summary"]["error_rate_percent"] == 66.67
    assert report["status_codes"] == {200: 1, 404: 1, 500: 1}


def test_top_ips():
    report = analyze([
        line(ip="10.0.0.1"),
        line(ip="10.0.0.1"),
        line(ip="10.0.0.2"),
    ], top=1)
    assert report["top_ips"] == [("10.0.0.1", 2)]


def test_suspicious_request_detection():
    entry = parse_line(line(target="/.env", status=404, ua="sqlmap/1.8"))
    assert entry is not None
    reasons = suspicious_reasons(entry)
    assert "sensitive_file_probe" in reasons
    assert "scanner_user_agent" in reasons


def test_malformed_line_count():
    report = analyze(["not a log line\n", line()], top=10)
    assert report["summary"]["malformed_lines"] == 1
    assert report["summary"]["total_requests"] == 1


def test_csv_output():
    report = analyze([line(status=200), line(status=404)], top=10)
    output = StringIO()
    write_csv_report(report, output)
    content = output.getvalue()
    assert "section,key,value,extra" in content
    assert "summary,total_requests,2" in content
    assert "status_code,404,1" in content
