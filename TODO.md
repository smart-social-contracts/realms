# TODO

## MVP

The current status of this project is WIP, but it's close to the final MVP.

The MVP should be able to:
- Allow any user to register with an IC identity
- Deposit money (ckBTC)
- The realm admin can transfer money to users or third-party canisters
- The datamodel, called GGG (Generalized Global Governance), defines all the objects and methods of a realm, so that realms can talk to each other. GGG maps entities from the realworld, such as citizens, organizations, proposals, land, etc.

Queriable and also in a nice chart on the web frontend:
- Show counters: population, money. 
- Show list of transactions
- Show list of users
- Show list of organizations
- Show app store and apps installed
- Show welcome message and thoughts of the realm admin
- The system allows to run Python code within the canister in runtime using `exec(...)` (from kybra-simple-shell). Also, every object has an `owner` attribute (from kybra-simple-db).

- The project should contain tests, for backend and for frontend.
- The backend tests are on IC (using the icp-dev-env container) and non-IC

IMPORTANT: one level up from this directory, there are a number of libraries and other projects ready to be used in this project. The projects are:
kybra-simple-db
kybra-simple-logging
kybra-simple-shell
kybra-simple-vault
Please use them whenver you can. You can import the libraries using pip (as they are in Pypi.org).


## Future ideas

- The realm admin is an AI trained with the contents of the `book` repository.
- The realm users can choose the realm admin from a market of AI admins in a kind of online store.
- In addition to realm admins, the online store will have apps that can be installed in the realm, such as types of vault, land registries, interfaces with traditional public administration national systems (tax, etc.)
- Allow users to create organizations
