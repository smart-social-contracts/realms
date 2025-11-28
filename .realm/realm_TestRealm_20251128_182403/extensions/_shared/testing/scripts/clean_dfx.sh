#!/bin/bash
# Script to clean up all dfx and pocket-ic processes, including zombies
# Shared utility for all extension tests

echo "🧹 Cleaning up dfx and pocket-ic processes..."

# Function to kill processes by name
kill_processes() {
    local process_name=$1
    # Find processes but exclude this script (clean_dfx.sh) and grep itself
    local pids=$(ps aux | grep "$process_name" | grep -v grep | grep -v clean_dfx | awk '{print $2}' || true)
    
    if [ -n "$pids" ]; then
        echo "  Killing $process_name processes: $pids"
        kill -9 $pids 2>/dev/null || true
        sleep 0.5
    fi
}

# Function to find and kill zombie processes by killing their parents
kill_zombie_parents() {
    local zombie_pids=$(ps aux | grep '<defunct>' | grep -v grep | awk '{print $2}' || true)
    
    if [ -n "$zombie_pids" ]; then
        echo "  Found zombie processes: $zombie_pids"
        for zombie_pid in $zombie_pids; do
            # Get parent PID
            parent_pid=$(ps -o ppid= -p "$zombie_pid" 2>/dev/null | tr -d ' ' || true)
            if [ -n "$parent_pid" ] && [ "$parent_pid" != "1" ]; then
                echo "    Killing parent process $parent_pid of zombie $zombie_pid"
                kill -9 "$parent_pid" 2>/dev/null || true
            fi
        done
        sleep 0.5
    fi
}

# Kill dfx processes
echo "🔍 Looking for dfx processes..."
kill_processes "dfx"

# Kill pocket-ic processes (including servers)
echo "🔍 Looking for pocket-ic processes..."
kill_processes "pocket-ic"
kill_processes "pocketic"

# Kill replica processes
echo "🔍 Looking for replica processes..."
kill_processes "replica"

# Kill icx-proxy processes
echo "🔍 Looking for icx-proxy processes..."
kill_processes "icx-proxy"

# Check for and clean up zombie processes
echo "🔍 Checking for zombie processes..."
kill_zombie_parents

# Final check
echo ""
echo "📊 Final status check:"
remaining_dfx=$(ps aux | grep -E 'dfx|pocket-ic|replica' | grep -v grep | grep -v clean_dfx || true)
remaining_zombies=$(ps aux | grep '<defunct>' | grep -v grep || true)

if [ -n "$remaining_dfx" ]; then
    echo "⚠️  Some processes are still running:"
    echo "$remaining_dfx"
else
    echo "✅ No dfx/pocket-ic processes running"
fi

if [ -n "$remaining_zombies" ]; then
    echo "⚠️  Some zombie processes remain:"
    echo "$remaining_zombies"
else
    echo "✅ No zombie processes found"
fi

echo ""
echo "✨ Cleanup complete!"
