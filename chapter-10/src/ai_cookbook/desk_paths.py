"""Deployment-owned paths; set before importing API/worker modules."""
import os
from pathlib import Path
STATE = Path(os.environ.get("AIC_STATE", "/state")).resolve()
SOURCES = Path(os.environ.get("AIC_SOURCES", "/data/knowledge")).resolve()
