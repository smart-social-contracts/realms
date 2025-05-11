#!/usr/bin/env python3
"""
Simplified Flask app for local development of Smart Social Contracts.
This version provides minimal API endpoints for testing the join functionality
without requiring Internet Computer specific dependencies.
"""

import json
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "OPTIONS"])

# In-memory storage for joined users (would be replaced with a proper database in production)
joined_users = set()


# Helper function to serialize JSON responses
def json_dumps(obj):
    return json.dumps(obj, separators=(",", ":"))


@app.route("/")
def home():
    return "Realms Local Development API"


@app.route("/get_realm_name", methods=["GET"])
@app.route("/get_realm_name_endpoint", methods=["GET"])  # IC-compatible endpoint name
@app.route("/api/v1/realm_name", methods=["GET"])
def handle_get_realm_name():
    """Get the name of the realm/organization"""
    try:
        # In a real implementation, this would come from your organization data
        # For now, return a default name
        name = "Realm"
        return json_dumps({"name": name})
    except Exception as e:
        logger.error(f"Error in get_realm_name: {str(e)}")
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

        # Add the user to our in-memory set
        joined_users.add(user_id)

        logger.info(f"User with ID {user_id} joined the organization")
        logger.info(f"Current joined users: {joined_users}")

        return json_dumps({"success": True})
    except Exception as e:
        logger.error(f"Error in user_join_organization: {str(e)}")
        return json_dumps({"error": str(e)}), 500


@app.route("/api/v1/users", methods=["GET"])
def handle_get_joined_users():
    """Get a list of all users who have joined"""
    try:
        return json_dumps({"users": list(joined_users)})
    except Exception as e:
        logger.error(f"Error in get_joined_users: {str(e)}")
        return json_dumps({"error": str(e)}), 500


if __name__ == "__main__":
    logger.info("Starting local development server for Smart Social Contracts")
    app.run(host="0.0.0.0", port=5000, debug=True)
