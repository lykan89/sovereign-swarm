# This allows you to do: from agents import ScoutAgent, SwarmCommander
# Instead of: from agents.scout import ScoutAgent

from .scout import ScoutAgent
from .commander import SwarmCommander
from .auditor import AuditorAgent

# You can also define versioning or shared constants here
__version__ = "1.0.0-2026-SOVEREIGN"