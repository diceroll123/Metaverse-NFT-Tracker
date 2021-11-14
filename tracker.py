import asyncio
import datetime
import functools
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, OrderedDict

import httpx
import pyexcel  # type: ignore
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


@run_in_executor
def export_to_spreadsheet(data: List[Dict[str, Any]]) -> None:
    pyexcel.save_as(records=data, dest_file_name="Metaverse_Purchases.xls")  # type: ignore


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

    # create spreadsheet
    sheet_data: List[Dict[str, Any]] = []
    for signature in signatures[::-1]:  # start from the oldest signature
        transaction = await get_transaction(signature)

        # first, we gather the interesting parts of the data

        # the payload
        result: Dict[str, Any] = transaction["result"]

        # metadata of the transaction (the good stuff)
        meta: Dict[str, Any] = result["meta"]

        # let's skip any errored transactions
        if meta["err"] is not None:
            continue

        # unix timestamp of the block's confirmation
        block_time: int = result["blockTime"]

        # metadata of the transaction (the good stuff)
        meta: Dict[str, Any] = result["meta"]

        # post-transaction token balances
        post_token_balances: List[Dict[str, Any]] = meta["postTokenBalances"]

        # pre-transaction token balances
        # if the buyer has never purchased this token before, it will be an empty list
        pre_token_balances: List[Dict[str, Any]] = meta["preTokenBalances"]

        # all addresses involved in the transaction
        account_keys: List[str] = result["transaction"]["message"]["accountKeys"]

        # the address of the account doing the purchase
        purchaser_address = account_keys[0]

        # the index of the metaverse wallet in this transaction, to track the income
        metaverse_wallet_index = account_keys.index(METAVERSE_WALLET_ADDRESS)

        # a list of the balances of the addresses involved in the transaction, before the transaction goes through
        pre_txn_balances: List[int] = meta["preBalances"]

        # a list of the balances of the addresses involved in the transaction, after the transaction goes through
        post_txn_balances: List[int] = meta["postBalances"]

        ##########

        # add to sheet data
        data: OrderedDict[str, Any] = OrderedDict({})
        data["Timestamp"] = datetime.datetime.fromtimestamp(block_time)
        data["Buyer"] = purchaser_address

        bought = 0
        post_token_balance = int(
            post_token_balances[0]["uiTokenAmount"]["uiAmountString"]
        )
        if len(pre_token_balances):
            before = int(pre_token_balances[0]["uiTokenAmount"]["uiAmountString"])
            bought = post_token_balance - before
        else:
            bought = post_token_balance

        data["Tokens Bought"] = bought

        data["Buyer's Token Count"] = post_token_balance

        data["$SOL Spent"] = (
            post_txn_balances[metaverse_wallet_index]
            - pre_txn_balances[metaverse_wallet_index]
        ) / ONE_SOL_IN_LAMPERTS

        data["Txn Signature"] = signature

        sheet_data.append(data)

    await export_to_spreadsheet(sheet_data)


if __name__ == "__main__":
    asyncio.run(main())
