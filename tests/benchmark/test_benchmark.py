from services.benchmark_service import run_benchmark


def test_benchmark():
    result = run_benchmark()
    assert "total_attacks" in result
