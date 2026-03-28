import httpx
import time

API_URL = "http://127.0.0.1:5000/classify_logs"

TEST_SCENARIOS = {
    "DB Connection Exhaustion": [
        "Connecting to database...",
        "Query taking too long to execute.",
        "Error: Database connection timeout.",
        "Connection pool drained."
    ],
    "Memory Pressure": [
        "Allocating new objects...",
        "Warning: High memory usage.",
        "Error: OutOfMemoryError - Java heap space.",
        "OOM killer invoked."
    ],
    "Upstream Timeout": [
        "Sending request to downstream service...",
        "Slow response detected from upstream.",
        "Error: Downstream service timed out causing upstream cascade."
    ],
    "Crash Injection": [
        "Service starting...",
        "Container died instantly.",
        "os._exit(1) called.",
        "Hard crash encountered."
    ],
    "Normal Operation": [
        "Health check passed.",
        "Request processed successfully in 45ms.",
        "User logged in.",
        "Starting service."
    ]
}

def run_tests():
    print("Starting Log Classification Engine Tests...\n")

    with httpx.Client() as client:
        for name, logs in TEST_SCENARIOS.items():
            print(f"Testing Scenario: {name}")

            start_time = time.time()
            response = client.post(API_URL, json={"logs": logs})
            end_time = time.time()

            latency = end_time - start_time

            if response.status_code == 200:
                result = response.json()
                print(f"  Predicted Root Cause : {result['root_cause']}")
                print(f"  Confidence           : {result['confidence']}")
                print(f"  Latency              : {latency:.4f} seconds")

                # Assert inference time is well under 3 seconds
                assert latency < 3.0, f"Latency {latency:.4f}s exceeded 3 seconds strict limit!"
                print("  => Latency requirement met.")
            else:
                print(f"  Request failed with status code {response.status_code}")
                print(f"  {response.text}")

            print("-" * 50)

    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    run_tests()
