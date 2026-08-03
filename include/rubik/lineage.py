"""Lineage assets for Rubik solver phase handoffs."""

from airflow.sdk import Asset


def phase_handoff_asset(phase: str) -> Asset:
    return Asset(f"rubik://solver/phase/{phase}")
