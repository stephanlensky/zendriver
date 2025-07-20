import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def import_from_path(file_path: Path | str) -> ModuleType:
    if isinstance(file_path, str):
        file_path = Path(file_path)

    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find module {module_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
