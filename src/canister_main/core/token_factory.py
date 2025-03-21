import ggg
from core.token_icrc1 import TokenICRC1
from core.token_internal import TokenInternal

def token_factory(symbol, token_core_type, **kwargs):
    if token_core_type == 'TokenICRC1':
        return ggg.Token.new(symbol, TokenICRC1.new(symbol, kwargs['principal']))
    elif token_core_type == 'TokenInternal':
        return ggg.Token.new(symbol, TokenInternal.new())
    raise Exception('Unsupported token_core_type "%s"' % token_core_type)

