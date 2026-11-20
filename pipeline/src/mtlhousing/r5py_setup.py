"""Configure r5py's JVM before r5py is imported.

r5py reads its options (including --max-memory) from the command line when it starts the
JVM, and the JVM can only start once per process. Call `import_r5py()` instead of
`import r5py` anywhere in the pipeline.
"""

from __future__ import annotations

import sys
from types import ModuleType

from mtlhousing.config import JVM_MAX_MEMORY


def import_r5py(max_memory: str = JVM_MAX_MEMORY) -> ModuleType:
    if "r5py" not in sys.modules and "--max-memory" not in sys.argv:
        sys.argv.extend(["--max-memory", max_memory])
    import r5py

    return r5py
