# GGG class implementation guidelines

1. Derive from `EntityLayer`

2. Constructor `new` must define an `id` (unique)
any other attributes will be saved as "attributes" 
set_relations / get_relations
properties
    to get/set an attribute
    to get/set a relation
other methods

3. the user access control is done at `EntityLayer` level

4. `to_dict` displays all the attributes and relations, but it is not recursive (that is, it does not call the `to_dict` method of the inner objects)




