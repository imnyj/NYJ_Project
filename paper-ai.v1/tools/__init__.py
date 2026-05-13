"""External tool adapters.

Two flavours of tools live here:

  * smolagents Tool subclasses — used by CodeAgent in the paper-ai
    pipeline (Librarian, Experimenter, etc.). These are imported as
    `from tools import ArxivSearchTool, FileReadTool, ...` by the
    agent files.

  * non-smolagents helpers (anthropic_client.py, batch_client.py,
    embeddings.py, ...) — used by infrastructure code outside the
    smolagents pipeline. Import explicitly from their submodule.

We re-export the smolagents tools at the package root for the
import style the original system used.
"""

from tools.arxiv_search import ArxivSearchTool
from tools.semantic_scholar_search import SemanticScholarSearchTool
from tools.file_io import (
    FileReadTool,
    FileWriteTool,
    DirectoryListTool,
)
from tools.upgrade_tool import (
    StageUpgradeTool,
    TestStagedUpgradeTool,
    FinalizeUpgradeTool,
    AbortUpgradeTool,
)

__all__ = [
    # Search
    "ArxivSearchTool",
    "SemanticScholarSearchTool",
    # File IO
    "FileReadTool",
    "FileWriteTool",
    "DirectoryListTool",
    # Self-upgrade (Commander only)
    "StageUpgradeTool",
    "TestStagedUpgradeTool",
    "FinalizeUpgradeTool",
    "AbortUpgradeTool",
]
