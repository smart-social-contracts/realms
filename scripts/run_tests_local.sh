#!/bin/bash

# Default mode is "test"
MODE=${1:-test}

if [ "$TEST_LOCAL" ]; then
    echo "Stopping any process using port 8000..."
    # Kill the process using port 8000 (if any), suppress errors if none is found
    kill -9 $(lsof -t -i:8000) 2>/dev/null

    echo "Waiting for port 8000 to be completely free..."
    # Wait until port 8000 is fully released
    while lsof -i:8000 >/dev/null; do 
        sleep 1
    done

    PYTHONPATH=$PWD/src/realm_backend TEST_LOCAL=$TEST_LOCAL python src/local/main.py &
    SERVER_PID=$!

    echo "Waiting for port 8000 to be open again..."
    # Wait until port 8000 is open (a process starts listening on it)
    while ! nc -z localhost 8000; do 
        sleep 1
    done

    if [ "$MODE" = "test" ]; then
        echo "Running tests..."
        PYTHONPATH=$PWD/src/realm_backend TEST_LOCAL=$TEST_LOCAL python -m pytest -s tests/tests.py
        TEST_EXIT_CODE=$?

        echo "Cleaning up test server..."
        kill -9 $SERVER_PID 2>/dev/null || true
        
        # Wait until port 8000 is fully released
        while lsof -i:8000 >/dev/null; do 
            sleep 1
        done
        
        exit $TEST_EXIT_CODE
    else
        echo "Server is running on port 8000. Press Ctrl+C to stop."
        # Wait for the server process
        wait $SERVER_PID
    fi
else
    TESTBENCH_NAME="testbench"
    # Only try to remove if container exists
    CONTAINER_IDS=$(docker ps -a --filter "name=$TESTBENCH_NAME" --format "{{.ID}}")
    if [ ! -z "$CONTAINER_IDS" ]; then
        docker rm -f $CONTAINER_IDS
    fi
    
    if [ "$MODE" = "test" ]; then
        RUN_TESTS=1 docker compose run $TESTBENCH_NAME
    else
        docker compose run $TESTBENCH_NAME
    fi
fi
