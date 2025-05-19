from api import status, user

if __name__ == "__main__":
    user.user_register("aaaaa-aa")
    print(user.user_get("aaaaa-aa"))
    print(status.get_status())
