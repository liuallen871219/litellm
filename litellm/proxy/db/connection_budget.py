"""Split each Postgres pool's connection budget between Prisma and the Rust core's SQLx pool.

Migration scaffolding. Prisma and SQLx share a database only while the Python gateway still runs Prisma
queries next to ported ones. These invariants hold until Prisma is gone:

- Operators set one `connection_limit` per pool (`database_connection_pool_limit`, a URL pin or
  `database_extra_connection_params`). The Rust share is carved out of it, never added on top, so a Rust
  pool does not grow the connection budget.
- The Rust share defaults to `RUST_RESERVED_CONNECTIONS`. An operator moves connections from Prisma to the
  Rust pool by setting `LITELLM_DATABASE_RUST_WRITER_CONNECTION_LIMIT` before startup, and `proxy_cli`
  clamps it so Prisma keeps at least one.
- The split is Python's. It is about Prisma and Prisma lives only in the Python gateway, so this module is
  deleted with Prisma. The process that starts the workers (`proxy_cli`) decides it once and hands each
  worker plain numbers.
- The Rust core takes a plain `max_connections` and never learns about the split. That is already its final
  interface, since the Rust gateway will pass `database_connection_pool_limit` straight to SQLx. If the Rust
  gateway ever starts the Python workers, the split moves into its startup code, not into a shared crate.
"""

from dataclasses import dataclass
from typing import Final

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

RUST_RESERVED_CONNECTIONS: Final = 2
RUST_CONNECTION_LIMIT_ENV_PREFIX: Final = "LITELLM_DATABASE_RUST_"
RUST_WRITER_CONNECTION_LIMIT_ENV_VAR: Final = f"{RUST_CONNECTION_LIMIT_ENV_PREFIX}WRITER_CONNECTION_LIMIT"


@dataclass(frozen=True, slots=True)
class ConnectionBudget:
    total: int
    python: int
    rust: int

    @classmethod
    def split(cls, total: int, rust_reserved: int = RUST_RESERVED_CONNECTIONS) -> "ConnectionBudget":
        """Each pool keeps at least one connection, so a total of 1 is the only case that ends up over it."""
        rust: Final = min(rust_reserved, max(1, total - 1))
        return cls(total=total, python=max(1, total - rust), rust=rust)


class RustConnectionLimits(BaseSettings):
    """The Rust pools' shares: what the operator asked for when `proxy_cli` reads it, and what `proxy_cli`
    granted when a worker does.

    An entrypoint that skips `proxy_cli` leaves Prisma's limit unsplit and the Rust pool at its reserve.
    """

    model_config = SettingsConfigDict(env_prefix=RUST_CONNECTION_LIMIT_ENV_PREFIX, extra="ignore", frozen=True)

    writer_connection_limit: PositiveInt = RUST_RESERVED_CONNECTIONS
