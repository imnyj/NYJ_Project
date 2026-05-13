"""Six smolagents-based agents.

Import order matters: each agent module instantiates a LiteLLMModel
at module load time, which calls get_api_key. So importing this
package unlocks the vault if it hasn't been already and resolves
all six keys eagerly.

For testing or dry-runs that should not require keys, import the
specific agent only when needed instead of using `from agents import *`.
"""

# We expose individual agents lazily — see commander.py which does
# `from agents.idea import idea_agent` etc. directly. No top-level
# imports here so importing the package alone doesn't trigger key
# resolution for unused agents.

__all__: list[str] = []
