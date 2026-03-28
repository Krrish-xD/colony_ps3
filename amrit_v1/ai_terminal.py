import time
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AI-Main")

def run_observability_loop():
    logger.info("Initializing Autonomic Observability System (Phase 2-5)...")
    
    last_log_count = 0
    while True:
        try:
            # Poll at 2-second intervals to mirror the UI live sync speed
            time.sleep(2)
            
            resp = requests.get("http://localhost:5001/api/state")
            if resp.status_code == 200:
                state = resp.json()
                logs = state.get("logs", [])
                
                # Fetch only NEW logs we haven't rendered yet
                if len(logs) > last_log_count:
                    new_logs = logs[last_log_count:]
                    for log in new_logs:
                        if "Alert" in log or "CHAOS" in log:
                            logger.warning(log)
                        elif "RCA" in log or "MEDIC" in log or "Remediation" in log:
                            logger.info(log)
                        else:
                            logger.info(log)
                    last_log_count = len(logs)
                
                # Health checking ping
                if state.get("status") == "Monitoring Traffic...":
                    # Only print health debugs sparingly to avoid terminal flood, just like old script
                    if int(time.time()) % 15 == 0:
                        logger.debug("No metric data or error logs collected. Swarm is healthy.")
                    
        except requests.exceptions.RequestException:
            logger.error("Connecting to AI Engine API...")
        except KeyboardInterrupt:
            logger.info("Deactivating Autonomous AI.")
            break

if __name__ == "__main__":
    run_observability_loop()
