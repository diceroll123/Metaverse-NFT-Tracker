"""
An attempt to see how much NFTs were resold for vis-a-vis their token mint
price.

**VERY** heavily adapted from Dice's code to similarly track NMC token sales.

Author: u/CaptainP a.k.a. umop u dn#8354
"""

import sys
import asyncio
import time
import datetime
from collections import OrderedDict
from pathlib import Path
from solana.rpc.async_api import AsyncClient
import tracker as t # Dice's code to download NMC token sales

MINT_TXN_SIG_FOLDER = Path("./mint_txn_sigs")
NFT_SIG_FOLDER = Path("./NFT_sigs")
SECONDARY_TXN_FOLDER = Path("./secondary_txn_sigs")

# the wallet where NFTs mint from
NFT_MINT_ADDRESS = "GBQF4aztREm6XaeSZyZfpCkqwQJmEAQHrusGVBDhmWQM"
SOLANART_SALES_ADDRESS = "EqBCGzzRGLcdoKprDiJFtoMGHYL3idfdcHqNvXjtQKGP"

for folder in [MINT_TXN_SIG_FOLDER,
               NFT_SIG_FOLDER,
               SECONDARY_TXN_FOLDER]:
    if not folder.exists():
        folder.mkdir()

# Need to have the results of token sales tracking already done:
if not Path("./Metaverse_Purchases.xls").is_file():
    print("""
          Cannot proceed; please download NMC token sales data first.
          This can be done by typing
          python tracker.py
          in the command line.
          """)
    sys.exit()


def balance_difference(result, acct_num: int):
    """
    Returns the balance difference before and after a transaction for a given
    account number.
    """
    after = result["meta"]["postBalances"][acct_num]
    before = result["meta"]["preBalances"][acct_num]

    return (after - before) / t.ONE_SOL_IN_LAMPORTS

async def main() -> None:
    ########################
    # GET MINT INFORMATION #
    ########################
    async with AsyncClient("https://api.mainnet-beta.solana.com") as client:

        # first cache all relevant signatures locally
        print("starting to fetch NFT mint data")
        mint_signatures = await t.fetch_all_signatures(client=client,
                                                       signature=NFT_MINT_ADDRESS)
        print("finished fetching NFT mint data!")
        newly_cached = 0
        start_time = time.monotonic()
        print("starting to cache new NFT mints")
        for signature in mint_signatures:
            # let's not waste I/O on re-caching
            cached = await t.is_cached(signature=signature,
                                       folder=MINT_TXN_SIG_FOLDER)
            if not cached:
                await t.fetch_transaction(client=client,
                                          signature=signature,
                                          folder=MINT_TXN_SIG_FOLDER)
                newly_cached += 1
        print("finished caching new NFT mints")

    if newly_cached:
        end_time = time.monotonic()

        print(
            f"New mints cached: {newly_cached:,} (Took {end_time - start_time} seconds)"
        )

    # create spreadsheet of mint info
    sheet_data: List[Dict[str, Any]] = []
    for signature in mint_signatures[::-1]: # start from the oldest signature
        transaction = await t.get_transaction(signature, MINT_TXN_SIG_FOLDER)

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

        # post-transaction token balances
        post_token_balances: List[Dict[str, Any]] = meta["postTokenBalances"]

        # pre-transaction token balances
        # if the buyer has never purchased this token before, it will be an empty list
        pre_token_balances: List[Dict[str, Any]] = meta["preTokenBalances"]

        # all addresses involved in the transaction
        account_keys: List[str] = result["transaction"]["message"]["accountKeys"]

        # the address of the account doing the minting
        minter_address = account_keys[0]
        NFT_sig = account_keys[1]

        # add to sheet data
        data: OrderedDict[str, Any] = OrderedDict({})
        data["Timestamp"] = datetime.datetime.fromtimestamp(block_time)
        data["Minter"] = minter_address
        data["Mint Txn Signature"] = signature
        data["NFT Signature"] = NFT_sig

        sheet_data.append(data)

    await t.export_to_spreadsheet(sheet_data, "Mint_Txns.xls")

    # #############################
    # # GET NMC TOKEN INFORMATION #
    # #############################
    # # this should already have been downloaded by executing tracker.py
    # # thinking of working with this separately, just want to get txn info here

    # NMC_token_sales = pd.read_excel("Metaverse_Purchases.xls")

    # NMC_token_sales["Unit price"] = (NMC_token_sales["$SOL Spent"]
    #                                  / NMC_token_sales["Tokens Bought"])

    # # make a copy that will be modified to decrement as matches are made
    # NMC_token_sales_counter = NMC_token_sales.copy()

    ###########################
    # GET SECONDARY SALE INFO #
    ###########################
    async with AsyncClient("https://api.mainnet-beta.solana.com") as client:

        # first cache all relevant signatures locally
        print("starting to fetch secondary sales data")
        resale_signatures = await t.fetch_all_signatures(client=client,
                                                         signature=SOLANART_SALES_ADDRESS,
                                                         earliest_time=1636966800)
        print("finished fetching secondary sales mint data!")
        newly_cached = 0
        start_time = time.monotonic()
        print("starting to cache new secondary sales")
        for signature in resale_signatures:
            # let's not waste I/O on re-caching
            cached = await t.is_cached(signature=signature,
                                       folder=SECONDARY_TXN_FOLDER)
            if not cached:
                await t.fetch_transaction(client=client,
                                          signature=signature,
                                          folder=SECONDARY_TXN_FOLDER)
                newly_cached += 1
        print("finished caching new secondary sales")

    if newly_cached:
        end_time = time.monotonic()

        print(
            f"New resales cached: {newly_cached:,} (Took {end_time - start_time} seconds)"
        )

    # create spreadsheet of resale info
    sheet_data: List[Dict[str, Any]] = []
    for signature in resale_signatures[::-1]: # start from the oldest signature
        transaction = await t.get_transaction(signature, SECONDARY_TXN_FOLDER)

        # the payload
        result: Dict[str, Any] = transaction["result"]

        # metadata of the transaction (the good stuff)
        meta: Dict[str, Any] = result["meta"]

        # let's skip any errored transactions
        if meta["err"] is not None:
            continue

        # unix timestamp of the block's confirmation
        block_time: int = result["blockTime"]

        # Is it a trade or a sale?
        # Sales have 18 accounts involved (trades have fewer, ~13)
        if len(result["transaction"]["message"]["accountKeys"]) == 18:
            buyer_price = balance_difference(result, 0)
            seller_price = balance_difference(result, 3)
            solanart_fee = balance_difference(result, 5)
            royalties = balance_difference(result, 9)
            NFT_sig = result["transaction"]["message"]["accountKeys"][10]
            seller = result["transaction"]["message"]["accountKeys"][3]
            buyer = result["transaction"]["message"]["accountKeys"][0]
        else:
            # it was a trade or transfer
            print(signature)
            continue

        # add to sheet data
        data: OrderedDict[str, Any] = OrderedDict({})
        data["Timestamp"] = datetime.datetime.fromtimestamp(block_time)
        data["Buyer paid"] = buyer_price
        data["Seller received"] = seller_price
        data["Solanart received"] = solanart_fee
        data["NMC received"] = royalties
        data["Secondary Sale Txn Signature"] = signature
        data["NFT Signature"] = NFT_sig
        data["Buyer wallet"] = buyer
        data["Seller wallet"] = seller

        sheet_data.append(data)

    await t.export_to_spreadsheet(sheet_data, "Secondary_Sales.xls")

if __name__ == "__main__":
    asyncio.run(main())
