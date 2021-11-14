import asyncio
import functools
import json
import time
from pathlib import Path
from typing import Any, Callable, List, Optional

import httpx
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import RPCResponse

# Where the Solana goes
METAVERSE_WALLET_ADDRESS = "Fwdp7bSAA1G4EsDn6DCkAuKSBRAJp7BjHutQptzQtzUG"

ONE_SOL_IN_LAMPERTS = 1_000_000_000  # Solana's version of Bitcoin's "Satoshi"

SIGNATURE_FOLDER = Path("./signatures")

if SIGNATURE_FOLDER.exists() is False:
    SIGNATURE_FOLDER.mkdir()


def json_file(signature: str) -> Path:
    """Returns the Path object for a transaction of a given signature."""
    return SIGNATURE_FOLDER / (signature + ".json")


def run_in_executor(func: Callable[..., Any]):
    """Turns blocking functions into async ones, in one line. (with decorator)"""

    @functools.wraps(func)
    async def wrapped(*args: Any, **kwargs: Any) -> Any:
        return await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(func, *args, **kwargs)
        )

    return wrapped


@run_in_executor
def is_cached(signature: str) -> bool:
    """Returns whether or not a transaction of a given signature has been cached."""

    return json_file(signature).exists()


@run_in_executor
def get_transaction(signature: str) -> RPCResponse:
    """Returns the transaction data of a given signature."""

    with open(json_file(signature), "r") as f:
        return json.loads(f.read())


@run_in_executor
def cache_transaction(signature: str, data: RPCResponse) -> None:
    """Write the transaction data to our local cache."""

    with open(json_file(signature), "w") as f:
        f.write(json.dumps(data, indent=4))  # pretty printed


async def fetch_transaction(client: AsyncClient, signature: str) -> RPCResponse:
    """Will fetch the transaction data from Solana, cache it, and then return the data"""

    try:
        transaction = await client.get_confirmed_transaction(signature)
    except httpx.HTTPStatusError:
        # probably a ratelimit error (HTTP Error 429)
        # Solana has a rate limit of 10s per 100 requests.
        # So, let's wait 11 seconds just to be sure,
        # and then do it again

        await asyncio.sleep(11)
        transaction = await client.get_confirmed_transaction(signature)

    await cache_transaction(signature, transaction)

    return transaction


async def fetch_all_signatures(client: AsyncClient) -> List[str]:
    """Grabs all signatures of transactions that includes the Metaverse Wallet's address.
    If the Metaverse address was at all in a transaction, it will be here.
    """

    # the "before" variable will be our makeshift pagination through all of the transactions
    before: Optional[str] = None

    signatures: List[str] = []

    while True:
        data = await client.get_signatures_for_address(
            METAVERSE_WALLET_ADDRESS, before=before
        )

        result = data["result"]  # type: ignore
        if len(result) == 0:
            # we hit the end!
            break

        for transaction in result:
            signatures.append(transaction["signature"])

        before = signatures[-1]

    return signatures


async def main() -> None:
    async with AsyncClient("https://api.mainnet-beta.solana.com") as client:

        # first, cache all of the signatures locally
        signatures = await fetch_all_signatures(client=client)
        newly_cached = 0
        start_time = time.monotonic()
        for signature in signatures:
            # let's not waste I/O on re-caching
            cached = await is_cached(signature=signature)
            if not cached:
                await fetch_transaction(client=client, signature=signature)
                newly_cached += 1

    if newly_cached:
        end_time = time.monotonic()

        print(
            f"New Transactions cached: {newly_cached:,} (Took {end_time - start_time} seconds)"
        )


if __name__ == "__main__":
    asyncio.run(main())
