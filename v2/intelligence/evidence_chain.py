def build_evidence_chain(service_name, logs, metrics, traces, root_cause, confidence):
    """
    Assembles a timestamped forensic evidence chain from all three signals.
    Returns a structured JSON object for dashboard display.
    """
    timeline = []

    # Add metric events
    if metrics:
        values = [float(v) for _, v in metrics[-10:]]  # Last 10 data points
        if values:
            spike = max(values)
            timeline.append({
                "t": "+0.0s",
                "signal": "metric",
                "event": f"P95 latency spiked to {spike:.0f}ms on {service_name}"
            })

    # Add log events (top 3 error logs)
    error_logs = [l for l in logs if "error" in l.lower()][:3]
    for i, log in enumerate(error_logs):
        timeline.append({
            "t": f"+0.{i+1}s",
            "signal": "log",
            "event": log[:200]  # Truncate long messages
        })

    # Add trace events
    if traces:
        slowest = max(traces, key=lambda s: s.get('duration_us', 0))
        dur_ms = slowest.get('duration_us', 0) / 1000
        timeline.append({
            "t": f"+0.{len(error_logs)+1}s",
            "signal": "trace",
            "event": f"Span {slowest.get('operation_name', 'unknown')}: duration={dur_ms:.0f}ms"
        })

    return {
        "service": service_name,
        "timeline": timeline,
        "classification": root_cause,
        "confidence": confidence,
    }
