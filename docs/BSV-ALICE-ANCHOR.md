# Alice historical anchor

The best located match for the requested early BSV “rabbit hole” reference is
**unwriter's Alice in BitcoinLand**. The original repository describes a
serverless website backed by a single transaction. Its loader references:

| Field | Observed value |
| --- | --- |
| Network | BSV mainnet |
| Transaction | `b742886801560f57b4dc824ce3a1719613d8b2d38530909fe988c1ca04cc82af` |
| Block | 566492 |
| Block hash | `000000000000000006cfc5b97a070212957574975f3b03d92fe4e009301b786d` |
| Block timestamp, UTC | 2019-01-23 12:54:04 |
| Serialized transaction bytes | 17360 |
| Data output | 1 |
| Data pushes | 19 pushes of 900 bytes; 17100 data bytes |

The pushed text begins “Big data time :) Crash through the looking glass” and
continues with the opening of *Through the Looking-Glass*. It is not a post
literally titled “Rabbit Hole,” and this observation does not establish the
first BSV data transaction or a block-size consensus activation. The author's
first repository commit uses a rabbit emoji. The connection to the user's
wording remains an interpretation, rather than a separate historical fact.

Sources inspected on November 22, 2026:

- [Creator's pinned source revision](https://github.com/unwriter/alice/blob/8b6c8fa05822de3cc3301fbe6c5dd2182f470dca/index.html).
- [First repository commit, 2019-01-23](https://github.com/unwriter/alice/commit/811c1e8ef957c17adba2ccaf5879d140a45df659).
- [Transaction](https://whatsonchain.com/tx/b742886801560f57b4dc824ce3a1719613d8b2d38530909fe988c1ca04cc82af).
- [Provider transaction JSON](https://api.whatsonchain.com/v1/bsv/main/tx/hash/b742886801560f57b4dc824ce3a1719613d8b2d38530909fe988c1ca04cc82af).
- [Provider block JSON](https://api.whatsonchain.com/v1/bsv/main/block/hash/000000000000000006cfc5b97a070212957574975f3b03d92fe4e009301b786d).

The serialized transaction was retrieved separately and its reversed double
SHA-256 matched the TXID. Its native output scripts are retained in Chisel's
separate `data-bsv-anchors/` feed with provenance and serialized hex. This
checks transaction-byte identity, not an independently verified inclusion
proof or signer attribution. The lookup does not add 63 transactions from its
containing block to scan coverage; only the one transaction was retrieved.

The daemon starts its forward `early` cursor at this block, inclusively, so
transactions in the same block are not missed. It also scans the confirmed
recent tip backward. `--anchor-height` or `--anchor-tx` can select a different
historical starting point in a fresh scan database.
