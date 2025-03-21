"""
Maintains backward compatibility by re-exporting from kybra_simple_db.
"""

from kybra_simple_db import CallContext

context_caller = CallContext()

__all__ = ['context_caller']
