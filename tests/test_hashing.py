"""Tests for hashing utilities."""
import tempfile
from pathlib import Path
from uepi_runner.hashing import sha256_file, sha256_string, sha256_csv


def test_sha256_string_deterministic():
    h1 = sha256_string("hello world")
    h2 = sha256_string("hello world")
    assert h1 == h2
    assert len(h1) == 64


def test_sha256_string_differs():
    h1 = sha256_string("hello")
    h2 = sha256_string("world")
    assert h1 != h2


def test_sha256_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test content\n")
        path = f.name
    h = sha256_file(path)
    assert len(h) == 64
    Path(path).unlink()


def test_sha256_csv_order_independent():
    """CSV hash should be deterministic regardless of row order."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("a,b\n1,2\n3,4\n")
        path1 = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("a,b\n3,4\n1,2\n")
        path2 = f.name

    h1 = sha256_csv(path1)
    h2 = sha256_csv(path2)
    assert h1 == h2

    Path(path1).unlink()
    Path(path2).unlink()
