from kybra_simple_db import *
from core.db import Entity
from core.execution import run_code, contains_function
from core.entity import GGGEntity

DEFAULT_EXTENSION_CODE_ORGANIZATION = \
    """
def heartbeat_hook():
    pass  #print('heartbeat 0')

def hook_join(organization, joiner):
    #if joiner.__class__.__name__ == 'User':
    #organization.token.mint(joiner.wallet.address(organization.token), 1)
    return 'ok'

def mint():
    return


def burn():
    return


def create_proposal():
    return
""".strip()

DEFAULT_EXTENSION_CODE_TOKEN = \
    """
def hook_mint(token, amount, address):
    return 'ok'

def hook_burn(token, amount, address):
    return 'ok'

def hook_transfer(token, from_address, to_address, amount):
    return 'ok'

""".strip()


# class SuperUser(User):
#     address = String(min_length=2, max_length=50)
#     gender = String(min_length=1, max_length=1)

#     @classmethod
#     def new(cls, name, age, address, **kwargs):
#         new_superuser = User.new(name, age, **kwargs)
#         new_superuser.address = address
#         return new_superuser


class ExtensionCode(GGGEntity):
    source_code = String(max_length=10000)  # Add a property for source_code
    programmable_entity = OneToMany(['Token', 'Organization'], 'extension_code')

    @classmethod
    def new(cls, source_code: str, **kwargs) -> 'ExtensionCode':
        new_entity = cls(**kwargs)
        new_entity.source_code = source_code
        return new_entity

    def run(self, function_name=None, function_signature="", locals={}):
        source_code = self.source_code
        if function_name:
            if not contains_function(source_code, function_name):
                raise Exception('Function "%s" not found in source code:\n%s' % (function_name, source_code))
            source_code = source_code + "\nresult = %s(%s)" % (
                function_name,
                function_signature,
            )
        return run_code(source_code, locals=locals)

    # @classmethod
    # def get_extension(cls, function_name, extension_codes):
    #     for extension_code in extension_codes:
    #         if contains_function(extension_code.source_code, function_name):
    #             return extension_code
    #     return None
