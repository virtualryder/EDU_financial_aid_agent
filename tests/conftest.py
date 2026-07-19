"""Shared test setup. Set the provenance signing secret ONCE, before any test module is imported, so
lookup_coa (signer) and assess_aid (verifier) use the same key for the P0-3 provenance gate."""
import os

os.environ.setdefault("PROVENANCE_SECRET", "p0-unit-provenance-secret")
