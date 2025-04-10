
class Realm(EntityLayer):
    @classmethod
    def new(cls, name, description=None):
        attributes = {EntityLayer._ID_PARAM_NAME: name, "description": description}
        return super().new(**attributes)


# list of realms update
# protocol version
# clusters from differerent ??? can send proposals to each other
