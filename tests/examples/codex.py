from ggg import User

# take all human users above of retirement
# transfer the pension money to them

RETIREMENT_AGE = 65

for user in User.instances():
    if user.human:
        if user.human.age > RETIREMENT_AGE:
            print(user)
