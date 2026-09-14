"""Test scaffolding for the rag_demo agents package.

The agent modules under test use relative imports (`from .query_expansion
import ...`), which only work if they're loaded as part of a real package.
We register a package for the `agents/` directory directly under a
deliberately synthetic name rather than importing it as `rag_demo.agents`:
a sibling example (llamaindex/rag/app/rag_demo) defines a *different*,
unrelated package that also happens to be named "rag_demo". If both were
ever imported in the same interpreter, whichever claimed the "rag_demo"
slot in sys.modules first would silently win for every subsequent
`import rag_demo...` in that process -- a synthetic, guaranteed-unique name
sidesteps that entirely.

query_expansion.py, validation.py, and correction.py also import
llama_index.llms.ollama, using it only as a constructor-argument type
hint. We prefer the real dependency when it's installed; we only fall
back to a minimal stand-in when it's completely absent, and only when
nothing has already touched the llama_index namespace, so we never risk
masking a genuine missing-dependency error for something else that
partially imported the real package first.
"""

import importlib
import sys
import types
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent

_PKG_ROOT = "rag_demo_agents_under_test"


def _install_ollama_stub() -> None:
    try:
        importlib.import_module("llama_index.llms.ollama")
        return  # the real dependency is installed; nothing to stub.
    except ImportError:
        pass

    if "llama_index" in sys.modules:
        # Something already partially populated the real llama_index
        # namespace (e.g. llama-index-core without the ollama plugin).
        # Don't guess at filling the gap -- that would risk masking a
        # genuine missing-dependency error for whatever imported it.
        return

    llama_index_pkg = types.ModuleType("llama_index")
    llama_index_pkg.__path__ = []
    sys.modules["llama_index"] = llama_index_pkg

    llms_pkg = types.ModuleType("llama_index.llms")
    llms_pkg.__path__ = []
    sys.modules["llama_index.llms"] = llms_pkg

    class Ollama:  # stand-in: only ever used as a type hint in this package.
        pass

    ollama_mod = types.ModuleType("llama_index.llms.ollama")
    ollama_mod.Ollama = Ollama
    sys.modules["llama_index.llms.ollama"] = ollama_mod


def _install_agents_package() -> None:
    if _PKG_ROOT not in sys.modules:
        pkg = types.ModuleType(_PKG_ROOT)
        pkg.__path__ = [str(AGENTS_DIR)]
        sys.modules[_PKG_ROOT] = pkg


_install_ollama_stub()
_install_agents_package()
