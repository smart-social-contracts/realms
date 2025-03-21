import execution
import ggg

class RpcClient:
    pass

class RpcServer:
    def process_instruction(instruction: dict) -> str:
        action = instruction.get("action")
        object_type = instruction.get("object_type")
        caller = execution.caller()

        if object_type != "User":
            return "Unsupported object type."

        if action == "create":
            # Only admins can create users
            # if not check_access(caller, "admin"):
            #     return "Access denied: Only admins can create users."

            user_data = instruction.get("data")
            if not user_data:
                return "Missing user data."

            user = ggg.User.new(
                id=user_data["id"],
                principal=user_data["principal"],
            )
            user.save()
            return f"User {user.id} created successfully."

        elif action == "call_method":
            user_id = instruction.get("object_id")
            method_name = instruction.get("method")
            args = instruction.get("args", [])
            if not user_id or not users_store.contains_key(user_id):
                return f"User with ID {user_id} does not exist."

            user = users_store.get(user_id)

            # Only editors or higher can call methods
            if not check_access(caller, "editor"):
                return "Access denied: Only editors or higher can call methods."

            # Dynamically call the method on the object
            try:
                method = getattr(user, method_name, None)
                if method is None or not callable(method):
                    return f"Method '{method_name}' not found on User."
                
                modifies_state = method_name in ["update_email"]  # Add all state-modifying methods here

                # Call the method
                result = method(*args)

                # If the method modifies the object, re-save it
                if modifies_state:
                    users_store.insert(user.id, user)
                
                return f"Method '{method_name}' executed successfully. Result: {result}"
            except Exception as e:
                return f"Error invoking method '{method_name}': {str(e)}"

        elif action == "delete":
            # Only admins can delete users
            if not check_access(caller, "admin"):
                return "Access denied: Only admins can delete users."

            user_id = instruction.get("object_id")
            if not user_id or not users_store.contains_key(user_id):
                return f"User with ID {user_id} does not exist."
            users_store.remove(user_id)
            return f"User {user_id} deleted successfully."

        return "Invalid instruction."



