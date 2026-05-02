"""End-to-end pipeline tests.

These tests run the full `python run.py` pipeline on a tiny dataset and
verify that all 9 CSVs are produced with the right shape, that the
verifier passes, and that the pipeline is byte-reproducible across
runs with the same seed.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_CSVS = {
    "items.csv", "customers.csv", "stores.csv", "promotions.csv",
    "invoice_headers.csv", "sales_lines.csv",
    "marketing_spend.csv", "support_tickets.csv", "nps_surveys.csv",
}


def _run_pipeline(out_dir: Path, *, seed: int = 42, n_customers: int = 20,
                  date_from: str = "2023-01-01",
                  date_till: str = "2023-12-31") -> None:
    cmd = [
        sys.executable, "run.py",
        "--seed", str(seed),
        "--market", "us",
        "--n-customers", str(n_customers),
        "--date-from", date_from,
        "--date-till", date_till,
        "--out-dir", str(out_dir),
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                            timeout=120)
    assert result.returncode == 0, (
        f"run.py failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.slow
def test_pipeline_produces_all_csvs(tmp_path):
    out = tmp_path / "synth"
    _run_pipeline(out)
    produced = {p.name for p in out.glob("*.csv")}
    missing = EXPECTED_CSVS - produced
    assert not missing, f"missing CSVs: {missing}"


@pytest.mark.slow
def test_pipeline_passes_verify(tmp_path):
    out = tmp_path / "synth"
    _run_pipeline(out)
    verify = subprocess.run(
        [sys.executable, "scripts/verify.py", str(out)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert verify.returncode == 0, (
        f"verify.py failed:\nstdout:\n{verify.stdout}\nstderr:\n{verify.stderr}"
    )
    assert "ALL CHECKS PASSED" in verify.stdout


@pytest.mark.slow
def test_pipeline_reproducible_with_same_seed(tmp_path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    _run_pipeline(out_a, seed=42)
    _run_pipeline(out_b, seed=42)
    for name in EXPECTED_CSVS:
        a_hash = hashlib.sha256((out_a / name).read_bytes()).hexdigest()
        b_hash = hashlib.sha256((out_b / name).read_bytes()).hexdigest()
        assert a_hash == b_hash, f"{name} differs between same-seed runs"


@pytest.mark.slow
def test_pipeline_different_seeds_diverge(tmp_path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    _run_pipeline(out_a, seed=42)
    _run_pipeline(out_b, seed=43)
    # invoice_headers should differ between seeds
    a_hash = hashlib.sha256((out_a / "invoice_headers.csv").read_bytes()).hexdigest()
    b_hash = hashlib.sha256((out_b / "invoice_headers.csv").read_bytes()).hexdigest()
    assert a_hash != b_hash
