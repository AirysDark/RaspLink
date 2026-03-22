````script
cd ~ && \
sudo apt update && \
sudo apt install -y unzip wget python3-venv python3-full && \
rm -rf RaspController backend_payload.zip && \
wget -O backend_payload.zip https://raw.githubusercontent.com/AirysDark/RaspLink/main/backend_payload.zip && \
unzip -o backend_payload.zip && \
cd RaspController && \

# Fix broken structure if needed
mkdir -p agent && \
mv api.py commands.py gpio.py monitor.py monitoring_v1.py process.py script_manager.py wol.py agent/ 2>/dev/null || true && \

# Create venv if missing
[ -d venv ] || python3 -m venv venv && \
source venv/bin/activate && \

# Install python deps safely
pip install --upgrade pip && \
pip install uvicorn fastapi pydantic psutil smbus2 && \

# Fix API launcher to use agent path
echo '#!/usr/bin/env bash
cd "$HOME/RaspController"
source venv/bin/activate
exec uvicorn agent.api:app --host 0.0.0.0 --port 8000' > start_api.sh && \
chmod +x start_api.sh && \

# Kill old server if running
pkill -f uvicorn || true && \

# Start backend
nohup ./start_api.sh > logs/api.log 2>&1 &

echo "✅ INSTALL COMPLETE"
````
