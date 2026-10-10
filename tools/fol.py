#!/usr/bin/env python3
"""Decrypt CombineLib .fol archives (cj/slr/mb) — static-RE'd from ComeOn.exe."""
from __future__ import annotations
import argparse, json, struct
from pathlib import Path

ENTRY = 0x88  # 34 dwords

def decrypt_toc_entry(entry: bytearray, key: int) -> None:
    for j in range(0x22):
        enc = struct.unpack_from("<I", entry, j * 4)[0]
        plain = (enc - 9 * (j ** 3) - key) & 0xFFFFFFFF
        struct.pack_into("<I", entry, j * 4, plain)

def decrypt_payload(blob: bytearray, key: int) -> None:
    nwords = len(blob) // 4
    for j in range(nwords):
        enc = struct.unpack_from("<I", blob, j * 4)[0]
        plain = (enc - key - 99 * (j * j)) & 0xFFFFFFFF
        struct.pack_into("<I", blob, j * 4, plain)

def extract_fol(path: Path, dest: Path) -> list[dict]:
    data = path.read_bytes()
    hdr = struct.unpack_from("<I", data, 0)[0]
    encrypted = bool(hdr & 0x80000000)
    count = hdr & 0x7FFFFFFF
    toc = bytearray(data[4 : 4 + count * ENTRY])
    keys = [0] * count
    if encrypted:
        key_off = len(data) - 4 * (97 + count)
        keys = list(struct.unpack_from(f"<{count}I", data, key_off))
        for i in range(count):
            e = bytearray(toc[i * ENTRY : (i + 1) * ENTRY])
            decrypt_toc_entry(e, keys[i])
            toc[i * ENTRY : (i + 1) * ENTRY] = e
    dest.mkdir(parents=True, exist_ok=True)
    index = []
    for i in range(count):
        e = bytes(toc[i * ENTRY : (i + 1) * ENTRY])
        name = e.split(b"\0", 1)[0].decode("latin1", "replace")
        off, size = struct.unpack_from("<II", e, 0x80)
        if size <= 0 or off + size > len(data):
            continue
        blob = bytearray(data[off : off + size])
        if encrypted:
            decrypt_payload(blob, keys[i])
        safe = name.replace("\\", "/").replace("..", "_")
        outp = dest / safe
        outp.parent.mkdir(parents=True, exist_ok=True)
        if outp.exists():
            outp = dest / f"{safe}__{i}"
        outp.write_bytes(blob)
        index.append({"name": name, "off": off, "size": size, "key": keys[i]})
    (dest / "_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fol", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()
    idx = extract_fol(args.fol, args.out)
    print(f"{args.fol.name}: {len(idx)} files -> {args.out}")

if __name__ == "__main__":
    main()
