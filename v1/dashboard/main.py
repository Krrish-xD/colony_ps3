import logging
import time
import requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import docker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Dashboard")

app = Flask(__name__)
CORS(app)

system_state = {
    "metrics": {},
    "logs": [
        "Intelligence node activated.",
        "Waiting for telemetry data..."
    ],
    "flagged_containers": [],
    "last_remediated": "-",
    "last_victim": "-",
    "remediation_timestamp": 0,
    "status": "Monitoring Traffic...",
    "chaos_index": 0
}

try:
    docker_client = docker.from_env()
except:
    docker_client = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(system_state)

@app.route('/api/anomaly', methods=['POST'])
def inject_anomaly():
    global system_state
    if not docker_client:
        return jsonify({"error": "Docker socket not found"}), 500
        
    try:
        containers = docker_client.containers.list(all=True)
        # Valid targets in Sock Shop
        valid_targets = ['catalogue', 'payment', 'shipping', 'carts', 'orders', 'edge-router', 'user']
        
        candidates = []
        for c in containers:
            for t in valid_targets:
                if t in c.name and "db" not in c.name: 
                    candidates.append((t, c))
                    break
                    
        if candidates:
            system_state['chaos_index'] = (system_state.get('chaos_index', 0) + 1) % len(candidates)
            service_name, target_container = candidates[system_state['chaos_index']]
            logger.warning(f"⚠️ ADMIN TRIGGERED CHAOS: Terminating {target_container.name}")
            
            try:
                if target_container.status == 'running':
                    target_container.kill()
            except Exception as e:
                logger.warning(f"Could not kill {target_container.name}: {e}")
            
            # Anomaly injected, send alert webhook to Alertmanager or let Prometheus catch it natively.
            # Here we just rely on Prometheus alerting Alertmanager, which sends to Intelligence!
            
            system_state['last_victim'] = service_name
            system_state['remediation_timestamp'] = time.time() # Reset SLA timer
            system_state['status'] = "Chaos Injected!"
            system_state['flagged_containers'] = [service_name]
            
            # Simulated logs for UI impact
            system_state['logs'].append(f"[Alert] Service {service_name} degraded and reported downtime!")
            if len(system_state['logs']) > 15:
                system_state['logs'] = system_state['logs'][-15:]
            
            return jsonify({"status": "success", "victim": service_name, "message": "Anomaly successfully administered."}), 200
            
        return jsonify({"status": "no targets eligible"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/events', methods=['POST'])
def handle_event():
    """ Webhook endpoint that the Remediation microservice hits after a successful restart """
    global system_state
    data = request.json
    logger.info(f"Received remediation event from backend: {data}")
    
    if data and data.get("action") == "restart_container":
        service = data.get("service")
        root_cause = data.get("root_cause", "Unknown Error")
        confidence = data.get("confidence", 0.99)
        
        system_state['last_remediated'] = service
        system_state['remediation_timestamp'] = time.time()
        system_state['status'] = f"Remediation Executed! (RCA: {root_cause} | Conf: {confidence*100}%)"
        system_state['last_victim'] = "-"
        system_state['flagged_containers'] = []
        
        system_state['logs'].append(f"-> RCA ENGINE Diagnosed: {root_cause} with {confidence*100}% confidence.")
        system_state['logs'].append(f"-> MEDIC ENGINE restarted service: {service}")
        
    return jsonify({"status": "acknowledged"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
