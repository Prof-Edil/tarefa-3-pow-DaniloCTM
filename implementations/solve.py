#!/usr/bin/env python3
import csv
import hashlib
import heapq
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMPOOL_PATH = ROOT / "data" / "mempool.csv"
EX2_PATH = ROOT / "data" / "ex02_txid_list.txt"
SOL1_PATH = ROOT / "solutions" / "exercise01.txt"
SOL2_PATH = ROOT / "solutions" / "exercise02.txt"

WEIGHT_LIMIT = 4_000_000
REQUIRED_TXID_EX1 = "4c50e3dad7f98bceb6441f96b23748dea84fbdb7cedd603441e6ea4a574d04a6"
REQUIRED_TXID_EX2 = "49ff8cccf1ca12179e9ae7a4760f550b5a18401b27e1e057604e27c3e10c08fb"


@dataclass(frozen=True)
class Tx:
    txid: str
    fee: int
    weight: int
    parents: tuple[str, ...]


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def load_mempool() -> dict[str, Tx]:
    txs: dict[str, Tx] = {}
    with MEMPOOL_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            parents = tuple(p.strip() for p in row[3].split(";") if p.strip()) if len(row) > 3 and row[3].strip() else ()
            tx = Tx(row[0].strip(), int(row[1]), int(row[2]), parents)
            txs[tx.txid] = tx
    return txs


def topo_sort_subset(mempool: dict[str, Tx], subset: set[str]) -> list[str]:
    ordered: list[str] = []
    visited: set[str] = set()

    def dfs(txid: str) -> None:
        if txid in visited:
            return
        visited.add(txid)
        for parent in mempool[txid].parents:
            if parent in subset:
                dfs(parent)
        ordered.append(txid)

    for txid in subset:
        dfs(txid)
    return ordered


def ancestors_of(mempool: dict[str, Tx], txid: str) -> set[str]:
    result: set[str] = set()

    def dfs(current: str) -> None:
        for parent in mempool[current].parents:
            if parent in result or parent not in mempool:
                continue
            result.add(parent)
            dfs(parent)

    dfs(txid)
    return result


def select_transactions() -> list[str]:
    mempool = load_mempool()
    children: dict[str, list[str]] = {txid: [] for txid in mempool}
    missing_parents: dict[str, int] = {}
    for txid, tx in mempool.items():
        missing_parents[txid] = len(tx.parents)
        for parent in tx.parents:
            if parent in mempool:
                children[parent].append(txid)

    selected: list[str] = []
    selected_set: set[str] = set()
    total_weight = 0

    def add_tx(txid: str) -> None:
        nonlocal total_weight
        if txid in selected_set:
            return
        selected.append(txid)
        selected_set.add(txid)
        total_weight += mempool[txid].weight
        for child in children[txid]:
            missing_parents[child] -= 1

    required_package = topo_sort_subset(mempool, ancestors_of(mempool, REQUIRED_TXID_EX1) | {REQUIRED_TXID_EX1})
    for txid in required_package:
        add_tx(txid)

    heap: list[tuple[float, int, int, str]] = []
    for txid, tx in mempool.items():
        if missing_parents[txid] == 0 and txid not in selected_set:
            heapq.heappush(heap, (-tx.fee / tx.weight, -tx.fee, tx.weight, txid))

    while heap:
        _, _, _, txid = heapq.heappop(heap)
        if txid in selected_set or missing_parents[txid] != 0:
            continue
        tx = mempool[txid]
        if total_weight + tx.weight > WEIGHT_LIMIT:
            continue
        add_tx(txid)
        for child in children[txid]:
            if missing_parents[child] == 0 and child not in selected_set:
                child_tx = mempool[child]
                heapq.heappush(
                    heap,
                    (-child_tx.fee / child_tx.weight, -child_tx.fee, child_tx.weight, child),
                )

    return selected


def solve_exercise_1() -> list[str]:
    selected = select_transactions()
    SOL1_PATH.write_text("\n".join(selected) + "\n", encoding="utf-8")
    return selected


def merkle_root_and_proof(txids: list[str], target_txid: str) -> tuple[str, list[str]]:
    level = [bytes.fromhex(txid) for txid in txids]
    index = txids.index(target_txid)
    proof: list[str] = []

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])

        sibling_index = index ^ 1
        proof.append(level[sibling_index].hex())

        next_level: list[bytes] = []
        for i in range(0, len(level), 2):
            next_level.append(sha256(level[i] + level[i + 1]))

        level = next_level
        index //= 2

    return level[0].hex(), proof


def solve_exercise_2() -> tuple[str, list[str]]:
    txids = [line.strip() for line in EX2_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    root, proof = merkle_root_and_proof(txids, REQUIRED_TXID_EX2)
    SOL2_PATH.write_text("\n".join([root, *proof]) + "\n", encoding="utf-8")
    return root, proof


def main() -> None:
    selected = solve_exercise_1()
    total_fee = 0
    total_weight = 0
    mempool = load_mempool()
    for txid in selected:
        total_fee += mempool[txid].fee
        total_weight += mempool[txid].weight

    root, proof = solve_exercise_2()
    print(f"exercise01: {len(selected)} txs, fee={total_fee}, weight={total_weight}")
    print(f"exercise02: root={root}, proof_len={len(proof)}")


if __name__ == "__main__":
    main()
