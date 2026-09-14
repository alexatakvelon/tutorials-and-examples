"""Test scaffolding for the rag_demo agents package.

These agents live inside rag_demo, whose real __init__.py pulls in redisvl
(the vector-store client used by the FastAPI app) even though the agents
themselves never touch it. Importing the agent modules the normal way, so
their own `from .xxx import Yyy` relative imports resolve, would otherwise
force every test run to have redisvl and a full llama-index-llms-ollama
install available. Since neither is needed for the logic under test here
(query expansion parsing, validation/correction JSON handling, and the
coordinator's step loop), we register lightweight stand-in packages in
sys.modules so the agents import as `rag_demo.agents.<module>` without
executing rag_demo/__init__.py or requiring those dependencies -- Ollama in
particular is used in these files only as a constructor-argument type hint.
"""

import sys
import types
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent
RAG_DEMO_DIR = AGENTS_DIR.parent


def _stub_module(name: str, **attrs) -> types.ModuleType:
    module = sys.modules.get(name) or types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_ollama_stub() -> None:
    if "llama_index.llms.ollama" in sys.modules:
        return
    _stub_module("llama_index")
    _stub_module("llama_index.llms")

    class Ollama:  # stand-in: only ever used as a type hint in this package.
        pass

    _stub_module("llama_index.llms.ollama", Ollama=Ollama)


def _install_rag_demo_package_stub() -> None:
    if "rag_demo" not in sys.modules:
        pkg = types.ModuleType("rag_demo")
        pkg.__path__ = [str(RAG_DEMO_DIR)]
        sys.modules["rag_demo"] = pkg
    if "rag_demo.agents" not in sys.modules:
        pkg = types.ModuleType("rag_demo.agents")
        pkg.__path__ = [str(AGENTS_DIR)]
        sys.modules["rag_demo.agents"] = pkg


_install_ollama_stub()
_install_rag_demo_package_stub()
