#!/bin/bash
# Double-click me. Sets up the whole factory on a new Mac.
cd "$(dirname "$0")"
bash ./install.sh
echo ""
echo "Closing in 10 seconds... (log: factory/logs/install.log)"
sleep 10
