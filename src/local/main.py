# pip install -r src/local//requirements.txt
# PYTHONPATH=src/canister_main python src/local/main.py


import importlib
import importlib.util
import os
import sys

PATH_LOCAL = r"/home/user/dev/the_project/app/src/local"
PATH_CANISTER = r"/home/user/dev/the_project/app/src/canister_main"


def load_local():
    if PATH_LOCAL not in sys.path:
        sys.path.insert(0, PATH_LOCAL)

    while PATH_CANISTER in sys.path:
        sys.path.remove(PATH_CANISTER)

    # print('load_local', '\n'.join(sys.path))

    # import core
    # import core.icrcledger as icrcledger
    # importlib.reload(core)
    # importlib.reload(icrcledger)


def load_canister():
    if PATH_CANISTER not in sys.path:
        sys.path.insert(0, PATH_CANISTER)

    while PATH_LOCAL in sys.path:
        sys.path.remove(PATH_LOCAL)

    # print('load_canister', '\n'.join(sys.path))

    import core

    importlib.reload(core)
    # import core.icrcledger as icrcledger
    # importlib.reload(core)
    # importlib.reload(icrcledger)


def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Register the module
    spec.loader.exec_module(module)
    return module


# load_local()

# load_module('icrcledger', r'/home/user/dev/the_project/app/src/local/core/icrcledger.py')

load_module("core", r"src/canister_main/core/__init__.py")
load_module("icrcledger", r"src/local/core/icrcledger.py")
# import core.icrcledger as icrcledger
# importlib.reload(icrcledger)
# load_canister()

import signal
import sys
import threading
import time
from datetime import datetime, timedelta

# from stats.snapshot import Snapshot
import core
import core.db as db
import core.execution as execution
from api.api import (create_user, get_organization_data, get_organization_list,
                     get_proposal_data, get_token_data, get_token_list,
                     get_user_data, get_user_list)
from core.logger import json_dumps
from flask import Flask, jsonify, request
from flask_cors import CORS
from ggg.base import audit, initialize, universe
from stats.snapshot import Snapshot

# load_local()


app = Flask(__name__)
CORS(
    app, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "OPTIONS"]
)  # Allow all methods including POST

# Global variable to control the heartbeat thread
heartbeat_thread_running = False


def heartbeat_function():
    """Function that runs periodically to execute organization extensions"""
    global heartbeat_thread_running
    last_run = None

    while heartbeat_thread_running:
        current_time = datetime.now()

        # Only run once per second
        if last_run is None or (current_time - last_run).total_seconds() >= 1:
            execution.execute_heartbeat()
            last_run = current_time

        # Sleep for a short time to prevent high CPU usage
        time.sleep(0.1)


def start_heartbeat():
    """Start the heartbeat thread"""
    global heartbeat_thread_running
    if not heartbeat_thread_running:
        heartbeat_thread_running = True
        thread = threading.Thread(target=heartbeat_function)
        thread.daemon = True  # Thread will stop when main program exits
        thread.start()


def stop_heartbeat():
    """Stop the heartbeat thread"""
    global heartbeat_thread_running
    heartbeat_thread_running = False


# API functions


@app.route("/get_universe", methods=["GET"])
@app.route("/api/v1/universe", methods=["GET"])
def get_universe():
    return json_dumps(universe())


@app.route("/get_realm_name", methods=["GET"])
@app.route("/get_realm_name_endpoint", methods=["GET"])  # IC-compatible endpoint name
@app.route("/api/v1/realm_name", methods=["GET"])
def handle_get_realm_name():
    """Get the name of the realm/organization"""
    try:
        # In a real implementation, this would come from your organization data
        # For example:
        # organization = Organization.get_default()
        # if organization:
        #     name = organization.name
        # else:
        #     name = "Default Realm"

        # For now, return a default name
        name = "Realm"
        return json_dumps({"name": name})
    except Exception as e:
        return json_dumps({"error": str(e)})


@app.route("/user_join_organization", methods=["POST"])
@app.route(
    "/user_join_organization_endpoint", methods=["POST", "GET"]
)  # IC-compatible endpoint name
@app.route("/api/v1/join", methods=["POST"])
def handle_user_join_organization():
    """Add a user to the organization/realm based on their principal ID"""
    try:
        # Handle both GET (IC-style) and POST requests
        if request.method == "GET":
            # Extract the user_id from query parameters for IC-style calls
            user_id = request.args.get("user_id", "")
        else:
            # Get the user principal from the request data (JSON body)
            data = request.get_json()
            if not data or "user_id" not in data:
                return json_dumps({"error": "Missing user_id parameter"}), 400
            user_id = data["user_id"]

        if not user_id:
            return json_dumps({"error": "Missing user_id parameter"}), 400

        # In a real implementation, you would add the user to your organization's members list
        # For example:
        # organization = Organization.get_default()
        # if organization:
        #     organization.add_member(user_id)
        #     organization.save()
        #     success = True
        # else:
        #     success = False

        # For now, simply log and return success
        print(f"User with ID {user_id} joined the organization")
        return json_dumps({"success": True})
    except Exception as e:
        return json_dumps({"error": str(e)}), 500


@app.route("/get_db", methods=["GET"])
@app.route("/api/v1/db", methods=["GET"])
def get_db():
    return db.get_db().dump_json(pretty=True)


@app.route("/get_audit", methods=["GET"])
@app.route("/api/v1/audit", methods=["GET"])
def get_audit():
    return json_dumps(Entity.db().get_audit())


@app.route("/get_stats", methods=["GET"])
@app.route("/api/v1/stats", methods=["GET"])
def get_stats():
    return json_dumps([i.to_dict() for i in Snapshot.instances()])


@app.route("/run_code", methods=["POST"])
@app.route("/api/v1/run_code", methods=["POST"])
def run_code():
    # Receive the uploaded file content
    source_code = request.data.decode(
        "ascii"
    )  # utf-8')  # Decode the binary data to a string
    result = execution.run_code(source_code)
    return json_dumps(result)


@app.route("/get_organization_list", methods=["GET"])
@app.route("/api/v1/organizations", methods=["GET"])
def handle_get_organization_list():
    """Get a list of all organizations"""
    return json_dumps(get_organization_list())


@app.route("/get_organization_data/<organization_id>", methods=["GET"])
@app.route("/api/v1/organizations/<organization_id>", methods=["GET"])
def handle_get_organization_data(organization_id):
    """Get details of a specific organization"""
    data = get_organization_data(organization_id)
    if data is None:
        return json_dumps({"error": "Organization not found"})
    return json_dumps(data)


@app.route("/get_user_list", methods=["GET"])
@app.route("/api/v1/users", methods=["GET"])
def handle_get_user_list():
    """Get a list of all users"""
    return json_dumps(get_user_list())


@app.route("/create_user", methods=["POST"])
@app.route("/api/v1/users", methods=["POST"])
def handle_create_user():
    """Create a new user"""
    try:
        user = create_user()
        return json_dumps(user), 201
    except Exception as e:
        return json_dumps({"error": str(e)}), 400


@app.route("/get_user_data/<user_id>", methods=["GET"])
@app.route("/api/v1/users/<user_id>", methods=["GET"])
def handle_get_user_data(user_id):
    """Get details of a specific user"""
    data = get_user_data(user_id)
    if data is None:
        return json_dumps({"error": "User not found"})
    return json_dumps(data)


@app.route("/get_token_list", methods=["GET"])
@app.route("/api/v1/tokens", methods=["GET"])
def handle_get_token_list():
    """Get a list of all tokens"""
    return json_dumps(get_token_list())


@app.route("/get_token_data/<token_id>", methods=["GET"])
@app.route("/api/v1/tokens/<token_id>", methods=["GET"])
def handle_get_token_data(token_id):
    """Get details of a specific token"""
    data = get_token_data(token_id)
    return json_dumps(data)


@app.route("/destroy_universe", methods=["POST"])
@app.route("/api/v1/destroy_universe", methods=["POST"])
def handle_destroy_universe():
    """Destroy the universe (clear the database)"""
    # from core.db_storage import db # TODO: broken
    db.clear()
    return json_dumps("OK")


@app.route("/get_proposal_data/<proposal_id>", methods=["GET"])
@app.route("/api/v1/proposal/<proposal_id>", methods=["GET"])
def handle_get_proposal_data(proposal_id):
    """Get details of a specific proposal"""
    try:
        result = get_proposal_data(proposal_id)
        if result:
            return json_dumps(result)
        return json_dumps({"error": "Proposal not found"}), 404
    except Exception as e:
        print(f"Error in get_proposal_data: {e}")
        # traceback.print_exc()
        return json_dumps({"error": str(e)}), 500


# other functions


@app.route("/greet", methods=["GET"])
@app.route("/api/v1/greet", methods=["GET"])
def greet():
    name = request.args.get("name", "Guest")
    return f"Hello, {name}!"


def signal_handler(signum, frame):
    print("\nReceived signal to shutdown. Stopping heartbeat thread...")
    stop_heartbeat()
    sys.exit(0)


if __name__ == "__main__":

    db.init_db()  # Initialize the database first
    initialize()  # Then initialize the application
    # start_heartbeat()  # Start the heartbeat thread

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        app.run(host="0.0.0.0", port=8000)
    finally:
        stop_heartbeat()  # Ensure heartbeat thread is stopped when app exits
