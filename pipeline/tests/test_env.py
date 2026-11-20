"""Smoke tests: the conda env has the right Java and r5py starts it with our memory cap."""

import jpype

from mtlhousing.r5py_setup import import_r5py


def test_geopandas_imports():
    import geopandas  # noqa: F401
    import pyogrio  # noqa: F401


def test_r5py_runs_on_jdk_21_or_newer():
    import_r5py()
    if not jpype.isJVMStarted():
        from r5py.util import start_jvm

        start_jvm()
    assert jpype.getJVMVersion()[0] >= 21, (
        f"JVM {jpype.getJVMVersion()} is too old. JAVA_HOME probably points to the "
        "system Java 17 instead of the conda env's OpenJDK 21."
    )


def test_jvm_max_memory_is_capped():
    import_r5py()
    max_bytes = jpype.java.lang.Runtime.getRuntime().maxMemory()
    gib = max_bytes / 2**30
    # The JVM reports slightly less than -Xmx; 6G should land between 5 and 6.5.
    assert 5 <= gib <= 6.5, f"JVM max memory is {gib:.2f} GiB, expected ~6"
