#!/usr/bin/env python3
"""
Run the Flask development server for local development
without needing to deploy to the Internet Computer
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Flask development server for Realms backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    # Set environment variables for Flask
    os.environ['FLASK_HOST'] = args.host
    os.environ['FLASK_PORT'] = str(args.port)
    os.environ['FLASK_DEBUG'] = '1' if args.debug else '0'
    
    # Import and run the Flask app
    from src.realm_backend.flask_main import app
    
    print(f"Starting Flask development server at http://{args.host}:{args.port}")
    if args.debug:
        print("Running in DEBUG mode")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
