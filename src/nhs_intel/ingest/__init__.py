"""Ingest scripts that convert published NHS England source files into the
CSV caches this project's sources consume. Kept separate from ``sources/``
so the serving layer stays pure and the monthly download stays out of the
request path.
"""
