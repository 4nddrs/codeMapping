#!/usr/bin/env bash
# Serve this menu on localhost (every page also opens straight from disk; this only
# adds a URL, e.g. for VS Code's port forwarding).
#   bash serve.sh                → http://localhost:8766/
#   bash serve.sh 9000           → another port
#   bash serve.sh 8766 0.0.0.0   → bind another address (a LAN/Tailscale IP, or all)
#   pkill -f 'http.server 8766'  → stop
# Survives the shell that started it (setsid), not a reboot.
set -u
PORT=${1:-8766}
IP=${2:-127.0.0.1}
cd "$(dirname "$0")"
pkill -f "^python3 -m http.server $PORT " 2>/dev/null   # anchored: never matches a shell whose cmdline merely mentions it
setsid nohup python3 -m http.server "$PORT" --bind "$IP" >/dev/null 2>&1 < /dev/null &
sleep 0.5
HOST=$IP; [ "$IP" = 127.0.0.1 ] && HOST=localhost; [ "$IP" = 0.0.0.0 ] && HOST=$(hostname -I | awk '{print $1}')
curl -sf -o /dev/null "http://$IP:$PORT/" && echo "menu: http://$HOST:$PORT/" || echo "serve.sh: server did not come up on $IP:$PORT" >&2
