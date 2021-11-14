
# Neopets Metaverse NFT Tracker

A simple script that spits out a spreadsheet after harvesting all transactions from the [Neopets Metaverse's Solana wallet](https://explorer.solana.com/address/Fwdp7bSAA1G4EsDn6DCkAuKSBRAJp7BjHutQptzQtzUG). Also conveniently caches them to a folder in the event you want to gather more data. At the time of writing, the 2,144 transactions processed so far takes up 22MB of disk space. When sales end, I will upload the spreadsheet to this repository.


## Interesting Tidbits

- 4 tokens were sold the day before launch to a [mystery account](7NnczUGzrxF2yeswUyKSYbKLjihxo7Nt5xP9syir3M13)
  - this used up 4 of the 250 tokens that would be sold at 1.0 SOL
  - below, this will be annotated as an italic `+number` to include it in stats while still separating it from regular launch-day purchases
- Exactly 1000 tokens were sold before the official launch time. *+4*
  - apparently this is common for NFT launches, due to pushing code early to \~try to be on time\~
- By the time the official launch began *(November 11th 2021, 1 AM PST)*:
  - the price was already 2.0 SOL per token.
  - 367 transactions occurred *+3*, with 296 unique buyers *+1*
  - Sales had already produced 1,504 SOL *+4*

## Run Locally

**This was written using Python 3.9, but Python 3.8 should also be fine at the very least**

Clone the project

```bash
  git clone https://github.com/diceroll123/Metaverse-NFT-Tracker
```

Go to the project directory

```bash
  cd Metaverse-NFT-Tracker
```

Install dependencies

```bash
  pip install -r requirements.txt
```

Start the script

```bash
  python tracker.py
```

If everything went well, after caching everything you'll find a `Metaverse_Purchases.xls` file in the folder.
## Relevant Links
 - [Neopets Metaverse's Solana wallet](https://explorer.solana.com/address/Fwdp7bSAA1G4EsDn6DCkAuKSBRAJp7BjHutQptzQtzUG)
 - [Neopets Metaverse's token minter](https://explorer.solana.com/address/HFuM3DaXBRN7zxDmgAX8KZeyh3MnMSCHYTXKHnVjLnGs)
    - Transactions here include tokens that have been minted to a wallet, and exchanged hands between two wallets
 - [Neopets Metaverse token distribution](https://explorer.solana.com/address/HFuM3DaXBRN7zxDmgAX8KZeyh3MnMSCHYTXKHnVjLnGs/largest)
    - shows the % of total supply for each owner of the token
- [/r/Neopets Discord Server](https://discord.gg/neopets)
