#!/usr/bin/env python3
"""Parse Candid text output from icp canister call into Python objects.

icp canister call outputs Candid text with hash-based field names when
the .did file is not available. This module:
1. Tokenizes the Candid text
2. Parses it into Python objects (dict/list/str/int/bool/None)
3. Maps hash-based field names back to their original names using the
   Candid IDL hash algorithm.
"""


def candid_hash(name: str) -> int:
    """Compute the Candid IDL hash for a field name."""
    h = 0
    for c in name:
        h = (h * 223 + ord(c)) % (2**32)
    return h


# All known field names from realm_backend Candid types
_KNOWN_FIELDS = [
    # RealmResponse
    "success", "data",
    # StatusRecord
    "version", "status", "users_count", "organizations_count", "realms_count",
    "mandates_count", "tasks_count", "transfers_count", "instruments_count",
    "codexes_count", "disputes_count", "licenses_count", "trades_count",
    "proposals_count", "votes_count", "commit", "commit_datetime", "extensions",
    "test_mode", "realm_name", "realm_logo", "realm_description",
    "realm_welcome_image", "realm_welcome_message", "user_profiles_count",
    "canisters", "registries", "dependencies", "python_version", "quarters",
    "is_quarter", "parent_realm_canister_id", "accounting_currency",
    "accounting_currency_decimals",
    # CanisterInfo
    "canister_id", "canister_type",
    # QuarterInfoRecord
    "name", "population",
    # UserGetRecord
    "principal", "profiles", "nickname", "avatar", "private_data", "assigned_quarter",
    # PaginationInfo
    "page_num", "page_size", "total_items_count", "total_pages",
    # ObjectsListRecord, ObjectsListRecordPaginated
    "objects", "pagination",
    # RealmResponseData (variant tags)
    "userGet", "error", "message", "objectsList", "objectsListPaginated",
    "extensionsList",
    # Crypto types
    "scope", "principal_id", "wrapped_dek", "envelopes", "scopes",
    "description", "groups", "members", "role",
    "envelope", "envelopeList", "scopeList", "group", "groupList", "groupMembers",
    # ExtensionCallArgs/Response
    "extension_name", "function_name", "args", "response",
    # Task types
    "task_id", "task_name", "task_status", "task_type", "task_data",
    "created_at", "updated_at", "result", "logs", "progress",
    # Zone types
    "zone_name", "zone_type", "zone_data", "zone_id",
    # Common
    "id", "type", "count", "items", "total", "page",
]

HASH_TO_NAME = {candid_hash(name): name for name in _KNOWN_FIELDS}


class _Token:
    __slots__ = ("type", "value")

    def __init__(self, type, value):
        self.type = type
        self.value = value


def _tokenize(text):
    """Tokenize Candid text into a list of tokens."""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # Skip whitespace
        if c in " \t\n\r":
            i += 1
            continue
        # String literal
        if c == '"':
            j = i + 1
            parts = []
            while j < n:
                if text[j] == '\\' and j + 1 < n:
                    nc = text[j + 1]
                    if nc == '"':
                        parts.append('"')
                    elif nc == '\\':
                        parts.append('\\')
                    elif nc == 'n':
                        parts.append('\n')
                    elif nc == 't':
                        parts.append('\t')
                    elif nc == 'r':
                        parts.append('\r')
                    else:
                        parts.append(text[j:j + 2])
                    j += 2
                elif text[j] == '"':
                    break
                else:
                    parts.append(text[j])
                    j += 1
            tokens.append(_Token("STR", "".join(parts)))
            i = j + 1
            continue
        # Punctuation
        if c == '{':
            tokens.append(_Token("LBRACE", c))
            i += 1
            continue
        if c == '}':
            tokens.append(_Token("RBRACE", c))
            i += 1
            continue
        if c == '(':
            tokens.append(_Token("LPAREN", c))
            i += 1
            continue
        if c == ')':
            tokens.append(_Token("RPAREN", c))
            i += 1
            continue
        if c == ';':
            tokens.append(_Token("SEMI", c))
            i += 1
            continue
        if c == ',':
            tokens.append(_Token("COMMA", c))
            i += 1
            continue
        if c == '=':
            tokens.append(_Token("EQ", c))
            i += 1
            continue
        if c == ':':
            tokens.append(_Token("COLON", c))
            i += 1
            continue
        if c == '+':
            tokens.append(_Token("PLUS", c))
            i += 1
            continue
        # Number (possibly negative, with underscores)
        if c.isdigit() or (c == '-' and i + 1 < n and text[i + 1].isdigit()):
            j = i
            if c == '-':
                j += 1
            while j < n and (text[j].isdigit() or text[j] == '_'):
                j += 1
            num_str = text[i:j].replace('_', '')
            tokens.append(_Token("NUM", int(num_str)))
            i = j
            continue
        # Identifier / keyword
        if c.isalpha() or c == '_':
            j = i
            while j < n and (text[j].isalnum() or text[j] == '_'):
                j += 1
            word = text[i:j]
            if word == "true":
                tokens.append(_Token("BOOL", True))
            elif word == "false":
                tokens.append(_Token("BOOL", False))
            elif word == "null":
                tokens.append(_Token("NULL", None))
            elif word in ("record", "vec", "variant", "opt", "principal", "blob",
                          "service", "func"):
                tokens.append(_Token("KW", word))
            elif word in ("nat", "nat8", "nat16", "nat32", "nat64",
                          "int", "int8", "int16", "int32", "int64",
                          "float32", "float64", "text", "bool", "empty",
                          "reserved"):
                tokens.append(_Token("TYPE", word))
            else:
                tokens.append(_Token("IDENT", word))
            i = j
            continue
        # Skip unknown
        i += 1
    return tokens


class _Parser:
    """Recursive descent parser for Candid text values."""

    def __init__(self, tokens, hash_map=None):
        self.tokens = tokens
        self.pos = 0
        self.hash_map = hash_map or HASH_TO_NAME

    def _peek(self, offset=0):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def _eat(self, expected_type=None):
        tok = self._peek()
        if tok is None:
            return None
        if expected_type and tok.type != expected_type:
            return None
        self.pos += 1
        return tok

    def parse_top(self):
        """Parse the outermost Candid value (usually wrapped in parens)."""
        tok = self._peek()
        if tok is None:
            return None
        if tok.type == "LPAREN":
            self._eat()
            val = self._parse_value()
            # Skip trailing comma and closing paren
            while self._peek() and self._peek().type in ("COMMA", "RPAREN"):
                self._eat()
            return val
        return self._parse_value()

    def _parse_value(self):
        tok = self._peek()
        if tok is None:
            return None

        if tok.type == "KW":
            if tok.value == "record":
                return self._parse_record()
            elif tok.value == "vec":
                return self._parse_vec()
            elif tok.value == "variant":
                return self._parse_variant()
            elif tok.value == "opt":
                self._eat()
                next_tok = self._peek()
                if next_tok and next_tok.type == "NULL":
                    self._eat()
                    return None
                return self._parse_value()
            elif tok.value == "principal":
                self._eat()
                s = self._eat("STR")
                return s.value if s else None
            elif tok.value == "blob":
                self._eat()
                s = self._eat("STR")
                return s.value if s else None
            else:
                self._eat()
                return self._parse_value()

        if tok.type == "STR":
            self._eat()
            return tok.value

        if tok.type == "NUM":
            self._eat()
            # Skip optional : type annotation
            if self._peek() and self._peek().type == "COLON":
                self._eat()  # :
                self._eat()  # type name
            return tok.value

        if tok.type == "BOOL":
            self._eat()
            return tok.value

        if tok.type == "NULL":
            self._eat()
            return None

        if tok.type == "TYPE":
            # Standalone type name (shouldn't happen normally), skip
            self._eat()
            return None

        # Skip anything else
        self._eat()
        return None

    def _resolve_field(self, tok):
        """Resolve a field name from a token (hash number or identifier)."""
        if tok.type == "NUM":
            return self.hash_map.get(tok.value, str(tok.value))
        elif tok.type == "IDENT":
            return tok.value
        return str(tok.value)

    def _parse_record(self):
        self._eat()  # record
        if not self._eat("LBRACE"):
            return {}

        result = {}
        while self._peek() and self._peek().type != "RBRACE":
            ftok = self._peek()
            if ftok is None or ftok.type == "RBRACE":
                break

            # Field name (hash number or identifier)
            if ftok.type in ("NUM", "IDENT"):
                self._eat()
                field_name = self._resolve_field(ftok)
            else:
                # Unexpected, skip
                self._eat()
                continue

            # =
            if self._peek() and self._peek().type == "EQ":
                self._eat()

            # Value
            val = self._parse_value()
            result[field_name] = val

            # ;
            if self._peek() and self._peek().type == "SEMI":
                self._eat()

        if self._peek() and self._peek().type == "RBRACE":
            self._eat()
        return result

    def _parse_vec(self):
        self._eat()  # vec
        if not self._eat("LBRACE"):
            return []

        result = []
        while self._peek() and self._peek().type != "RBRACE":
            val = self._parse_value()
            if val is not None:
                result.append(val)

            if self._peek() and self._peek().type == "SEMI":
                self._eat()

        if self._peek() and self._peek().type == "RBRACE":
            self._eat()
        return result

    def _parse_variant(self):
        self._eat()  # variant
        if not self._eat("LBRACE"):
            return {}

        result = {}
        ftok = self._peek()
        if ftok and ftok.type in ("NUM", "IDENT"):
            self._eat()
            field_name = self._resolve_field(ftok)

            if self._peek() and self._peek().type == "EQ":
                self._eat()
                val = self._parse_value()
                result[field_name] = val
            else:
                # Unit variant (no value)
                result[field_name] = None

            if self._peek() and self._peek().type == "SEMI":
                self._eat()

        if self._peek() and self._peek().type == "RBRACE":
            self._eat()
        return result


def parse_candid(text, hash_map=None):
    """Parse Candid text output into a Python object.

    Args:
        text: Raw Candid text output from icp canister call
        hash_map: Optional dict mapping hash ints to field names.
                  Defaults to HASH_TO_NAME built from known backend types.

    Returns:
        Parsed Python object (dict, list, str, int, bool, or None)
    """
    tokens = _tokenize(text)
    parser = _Parser(tokens, hash_map=hash_map)
    return parser.parse_top()
