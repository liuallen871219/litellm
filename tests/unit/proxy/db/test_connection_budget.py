from typing import Final

import pytest

from litellm.proxy.db.connection_budget import ConnectionBudget, RustConnectionLimits


@pytest.mark.parametrize("total", range(2, 41))
def test_split_stays_within_the_total_and_keeps_both_pools_open(total: int) -> None:
    budget: Final = ConnectionBudget.split(total)

    assert budget.python + budget.rust == total
    assert budget.python >= 1
    assert budget.rust >= 1


@pytest.mark.parametrize(
    ("total", "rust_reserved", "python", "rust"),
    [(10, 2, 8, 2), (3, 2, 1, 2), (2, 2, 1, 1), (1, 2, 1, 1)],
    ids=["reserve_taken", "reserve_fits_exactly", "reserve_clamped", "one_connection_per_pool_floor"],
)
def test_split_takes_the_rust_reserve_out_of_the_total(total: int, rust_reserved: int, python: int, rust: int) -> None:
    budget: Final = ConnectionBudget.split(total, rust_reserved=rust_reserved)

    assert (budget.python, budget.rust) == (python, rust)


def test_workers_read_the_rust_share_proxy_cli_exported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_DATABASE_RUST_WRITER_CONNECTION_LIMIT", "3")

    assert RustConnectionLimits().writer_connection_limit == 3
