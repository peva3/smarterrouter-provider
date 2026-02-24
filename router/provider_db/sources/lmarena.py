"""
LMArena (formerly LMSYS) - ELO ratings from lmarena.ai.
Note: lmarena.ai requires JavaScript, so we use fallback data.
"""

from typing import Dict
from .lmsys_arena import FALLBACK_ELO, fetch_lmsys_arena


def fetch_lmarena() -> Dict[str, int]:
    """
 ELO ratings from lmarena.ai.
    Since lmarena.ai requires JavaScript, we use the same fallback as LMSYS.
    """
    return fetch_lmsys_arena()
