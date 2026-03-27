#!/bin/bash

# Script to dispatch Jules AI cloud instances for the Colony PS3 Project

PROJECT_DIR="/home/xd/Coding/colony_ps3"
PROMPTS_DIR="$PROJECT_DIR/jules_prompts"

cd "$PROJECT_DIR" || exit 1

echo "====================================================="
echo "🚀 PHASE A: FOUNDATION & OBSERVABILITY (Instances 1-3)"
echo "====================================================="
echo "Dispatching Jules Instance 1 (Services)..."
cat "$PROMPTS_DIR/01_instance_services.md" | jules new

echo "Dispatching Jules Instance 2 (OTel & Prometheus)..."
cat "$PROMPTS_DIR/02_instance_otel_prom.md" | jules new

echo "Dispatching Jules Instance 3 (Loki & Jaeger)..."
cat "$PROMPTS_DIR/03_instance_loki_jaeger.md" | jules new

echo ""
echo "🛑 FAILURE PAUSE 1 🛑"
echo "Wait for Jules Phase A sessions to complete on the cloud."
echo "Use 'jules remote list --session' to check their status."
echo "Use 'jules remote pull --session <ID> --apply' to pull the code."
echo "Verify endpoints return 200 and telemetry appears."
read -p "Press [Enter] to proceed to Phase B once validated..."

echo "====================================================="
echo "🧠 PHASE B: INTELLIGENCE & REMEDIATION (Instances 4-5)"
echo "====================================================="
echo "Dispatching Jules Instance 4 (RCA Engine)..."
cat "$PROMPTS_DIR/04_instance_rca_engine.md" | jules new

echo "Dispatching Jules Instance 5 (Remediation Execution)..."
cat "$PROMPTS_DIR/05_instance_remediation.md" | jules new

echo ""
echo "🛑 FAILURE PAUSE 2 🛑"
echo "Wait for Jules Phase B sessions to complete."
echo "Simulate an Alertmanager webhook to the RCA engine and verify docker restarting logic."
read -p "Press [Enter] to proceed to Phase C once validated..."

echo "====================================================="
echo "🖥️ PHASE C: UI, CHAOS, & INTEGRATION (Instances 6-8)"
echo "====================================================="
echo "Dispatching Jules Instance 6 (React Dashboard)..."
cat "$PROMPTS_DIR/06_instance_dashboard.md" | jules new

echo "Dispatching Jules Instance 7 (Chaos Engineering)..."
cat "$PROMPTS_DIR/07_instance_chaos.md" | jules new

echo "Dispatching Jules Instance 8 (Master Deploy Integration)..."
cat "$PROMPTS_DIR/08_instance_deploy.md" | jules new

echo ""
echo "✅ Pipeline dispatch complete."
echo "Wait for final sessions to finish, pull the code, then run 'docker-compose up' to test the 15-second end-to-end loop."
