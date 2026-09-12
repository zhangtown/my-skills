"""Stable contract constants for cross-skill bundle consumers.

This module deliberately has a unique name.  The review skill also has a
``query_contract`` module, and both skills can be loaded in one Python process.
Keeping the manifest contract constant here prevents Python's global module
cache from binding the search validator to the review module by accident.
"""

from __future__ import annotations


CONTRACT_VERSION = "rls.v1"
