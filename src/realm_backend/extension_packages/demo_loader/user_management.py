from ggg import (
    Human,
    User,
)
from kybra_simple_logging import get_logger
from .config import NUM_USERS

logger = get_logger("demo_loader.user_management")

# Number of users to create per step
USERS_PER_BATCH = 100

# Lists of names for generating realistic user data
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna",
    "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Frank", "Debra",
    "Alexander", "Rachel", "Patrick", "Catherine", "Raymond", "Carolyn", "Jack", "Janet",
    "Dennis", "Ruth", "Jerry", "Maria", "Tyler", "Heather", "Aaron", "Diane",
    "Jose", "Virginia", "Adam", "Julie", "Henry", "Joyce", "Nathan", "Victoria",
    "Douglas", "Olivia", "Zachary", "Kelly", "Peter", "Christina", "Kyle", "Lauren",
    "Walter", "Joan", "Ethan", "Evelyn", "Jeremy", "Judith", "Harold", "Megan",
    "Keith", "Cheryl", "Christian", "Martha", "Roger", "Andrea", "Noah", "Frances",
    "Gerald", "Hannah", "Carl", "Jacqueline", "Terry", "Ann", "Sean", "Gloria",
    "Austin", "Jean", "Arthur", "Kathryn", "Lawrence", "Alice", "Jesse", "Teresa",
    "Dylan", "Sara", "Bryan", "Janice", "Joe", "Doris", "Jordan", "Roberta",
    "Billy", "Julia", "Bruce", "Marie", "Albert", "Madison", "Willie", "Grace",
    "Gabriel", "Judy", "Alan", "Theresa", "Juan", "Beverly", "Logan", "Denise",
    "Wayne", "Marilyn", "Ralph", "Amber", "Roy", "Danielle", "Eugene", "Rose",
    "Randy", "Brittany", "Vincent", "Diana", "Russell", "Abigail", "Louis", "Natalie",
    "Philip", "Jane", "Bobby", "Lori", "Johnny", "Alexis", "Bradley", "Tiffany"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reed", "Stewart", "Morris", "Morales",
    "Murphy", "Cook", "Rogers", "Morgan", "Peterson", "Cooper", "Reed", "Bailey",
    "Bell", "Gomez", "Kelly", "Howard", "Ward", "Cox", "Diaz", "Richardson",
    "Wood", "Watson", "Brooks", "Bennett", "Gray", "James", "Reyes", "Cruz",
    "Hughes", "Price", "Myers", "Long", "Foster", "Sanders", "Ross", "Morales",
    "Powell", "Sullivan", "Russell", "Ortiz", "Jenkins", "Gutierrez", "Perry", "Butler",
    "Barnes", "Fisher", "Henderson", "Coleman", "Simmons", "Patterson", "Jordan", "Hughes",
    "Alexander", "Fleming", "Rose", "Stone", "Hawkins", "Dunn", "Riley", "Gardner",
    "Lloyd", "Hudson", "Griffin", "Diaz", "Hayes", "Myers", "Ford", "Hamilton",
    "Graham", "Sullivan", "Wallace", "Woods", "Cole", "West", "Jordan", "Owens",
    "Reynolds", "Fisher", "Ellis", "Harrison", "Gibson", "McDonald", "Cruz", "Marshall",
    "Ortiz", "Gomez", "Murray", "Freeman", "Wells", "Webb", "Simpson", "Stevens",
    "Tucker", "Porter", "Hunter", "Hicks", "Crawford", "Henry", "Boyd", "Mason",
    "Morris", "Kennedy", "Warren", "Dixon", "Ramos", "Reyes", "Burns", "Gordon",
    "Shaw", "Wagner", "Hunter", "Romero", "Hunt", "Hicks", "Black", "Daniels",
    "Palmer", "Mills", "Nichols", "Grant", "Knight", "Ferguson", "Rose", "Stone",
    "Hawkins", "Dunn", "Riley", "Gardner", "Lloyd", "Hudson", "Griffin", "Diaz"
]

def generate_deterministic_name(index):
    """Generate a deterministic name based on the index.
    
    Args:
        index (int): The index of the user
        
    Returns:
        dict: A dictionary containing the username and human name
    """
    # Use modulo to cycle through the name lists
    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    
    return {
        "name": f"{first_name.lower()}_{last_name.lower()}",  # username format
        "human_name": f"{first_name} {last_name}"  # full name format
    }

def run(batch):
    """Create users and humans for the demo in batches."""

    # Calculate start and end indices for this batch
    start_idx = batch * USERS_PER_BATCH
    end_idx = min(start_idx + USERS_PER_BATCH, NUM_USERS)

    if start_idx >= NUM_USERS:
        return f"All {NUM_USERS} users have been created"

    logger.info(f"Creating users {start_idx + 1} to {end_idx} of {NUM_USERS}")

    # Create users and their corresponding humans
    users = []
    humans = []
    
    for i in range(start_idx, end_idx):
        # Generate deterministic name for this user
        user_data = generate_deterministic_name(i)
        human = Human(name=user_data["human_name"])
        user = User(name=user_data["name"])
        humans.append(human)
        users.append(user)

    logger.info(f"Created {len(users)} users and {len(humans)} humans in this batch")

    # Calculate progress
    total_created = end_idx
    remaining = NUM_USERS - total_created
    progress = (total_created / NUM_USERS) * 100

    return f"Created {len(users)} users and {len(humans)} humans in this batch number {batch}. Progress: {progress:.1f}% ({total_created}/{NUM_USERS}). {remaining} users remaining."

