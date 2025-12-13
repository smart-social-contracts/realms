#!/bin/bash
# Script to clean up all dfx and pocket-ic processes, including zombies

echo "🧹 Cleaning up dfx and pocket-ic processes..."

# Check if we need sudo
USE_SUDO=""
if [ "$(id -u)" != "0" ]; then
    # Check if there are any root processes to kill
    if ps aux | grep -E 'dfx|pocket-ic|replica' | grep -v grep | grep -v clean_dfx | grep '^root' > /dev/null 2>&1; then
        echo "⚠️  Root processes detected. Using sudo for cleanup..."
        USE_SUDO="sudo"
    fi
fi

# Function to kill processes by name with retry
kill_processes() {
    local process_name=$1
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Find processes but exclude this script (clean_dfx.sh) and grep itself
        local pids=$($USE_SUDO ps aux | grep "$process_name" | grep -v grep | grep -v clean_dfx | awk '{print $2}' || true)
        
        if [ -z "$pids" ]; then
            if [ $attempt -eq 1 ]; then
                echo "  No $process_name processes found"
            fi
            break
        fi
        
        if [ $attempt -eq 1 ]; then
            echo "  Killing $process_name processes (attempt $attempt): $pids"
        else
            echo "  Retrying $process_name processes (attempt $attempt): $pids"
        fi
        
        # Kill each PID individually to avoid issues
        for pid in $pids; do
            $USE_SUDO kill -9 "$pid" 2>/dev/null || true
        done
        
        sleep 1
        attempt=$((attempt + 1))
    done
}

# Function to find and kill zombie processes by killing their parents
kill_zombie_parents() {
    local zombie_pids=$($USE_SUDO ps aux | grep '<defunct>' | grep -v grep | awk '{print $2}' || true)
    
    if [ -n "$zombie_pids" ]; then
        echo "  Found zombie processes: $zombie_pids"
        for zombie_pid in $zombie_pids; do
            # Get parent PID
            parent_pid=$($USE_SUDO ps -o ppid= -p "$zombie_pid" 2>/dev/null | tr -d ' ' || true)
            if [ -n "$parent_pid" ] && [ "$parent_pid" != "1" ]; then
                echo "    Killing parent process $parent_pid of zombie $zombie_pid"
                $USE_SUDO kill -9 "$parent_pid" 2>/dev/null || true
            fi
        done
        sleep 1
    fi
}

# Step 1: Kill bash scripts that might be running dfx/realms commands
echo "🔍 Looking for bash scripts running dfx/realms commands..."
bash_pids=$($USE_SUDO ps aux | grep bash | grep -E 'realms|dfx' | grep -v grep | grep -v clean_dfx | awk '{print $2}' || true)
if [ -n "$bash_pids" ]; then
    echo "  Killing bash scripts: $bash_pids"
    for pid in $bash_pids; do
        $USE_SUDO kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
fi

# Step 2: Kill dfx processes
echo "🔍 Looking for dfx processes..."
kill_processes "dfx start"
kill_processes "dfx"

# Step 3: Kill pocket-ic processes (parent first, then children)
echo "🔍 Looking for pocket-ic processes..."
kill_processes "pocket-ic --port"
kill_processes "pocket-ic --run-as"
kill_processes "pocket-ic"
kill_processes "pocketic"

# Step 4: Kill replica processes
echo "🔍 Looking for replica processes..."
kill_processes "replica"

# Step 5: Kill icx-proxy processes
echo "🔍 Looking for icx-proxy processes..."
kill_processes "icx-proxy"

# Step 6: Free up dfx ports (kill any process using them)
echo "🔍 Checking dfx ports (8000, 8070, 4943)..."
for port in 8000 8070 4943; do
    port_pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$port_pids" ]; then
        echo "  Found processes on port $port: $port_pids"
        for pid in $port_pids; do
            proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            echo "    Killing $proc_name (PID $pid) on port $port"
            $USE_SUDO kill -9 "$pid" 2>/dev/null || true
        done
    else
        echo "  Port $port is free"
    fi
done

# Step 7: Check for and clean up zombie processes
echo "🔍 Checking for zombie processes..."
kill_zombie_parents

# Step 8: Final aggressive cleanup pass
echo "🔍 Final cleanup pass..."
remaining=$($USE_SUDO ps aux | grep -E 'dfx|pocket-ic|replica|icx-proxy' | grep -v grep | grep -v clean_dfx | awk '{print $2}' || true)
if [ -n "$remaining" ]; then
    echo "  Cleaning up remaining processes: $remaining"
    for pid in $remaining; do
        $USE_SUDO kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
fi

# Final check
echo ""
echo "📊 Final status check:"
remaining_dfx=$($USE_SUDO ps aux | grep -E 'dfx|pocket-ic|replica' | grep -v grep | grep -v clean_dfx || true)
remaining_zombies=$($USE_SUDO ps aux | grep '<defunct>' | grep -v grep || true)

if [ -n "$remaining_dfx" ]; then
    echo "⚠️  Some processes are still running:"
    echo "$remaining_dfx"
    echo ""
    echo "💡 Try running with sudo: sudo $0"
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
