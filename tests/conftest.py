import importlib.util
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))  # so tests can `import utils`, `import config`


def load_step(filename):
    """Import a numbered pipeline script such as '01_fetch_openaq.py' (not a valid module name)."""
    spec = importlib.util.spec_from_file_location("step_" + Path(filename).stem, SRC / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
