#!/usr/bin/env python3
"""Rebind DNS for ghe.lab: public A until flip file exists, then loopback."""


import os
import socket
import struct
import threading
import time

GHE_NAME = os.environ.get("GHE_NAME", "ghe.lab").rstrip(".").lower()
PUBLIC_IP = os.environ.get("PUBLIC_IP", "1.1.1.1")
REBIND_IP = os.environ.get("REBIND_IP", "127.0.0.1")
SHARED_DIR = os.environ.get("SHARED_DIR", "/shared")
LOG_DIR = os.environ.get("LOG_DIR", "/logs")
BIND = os.environ.get("DNS_BIND", "0.0.0.0")
PORT = int(os.environ.get("DNS_PORT", "53"))
FORWARDER = os.environ.get("FORWARDER", "8.8.8.8")
FLIP_PATH = os.path.join(SHARED_DIR, "rebind_flip")
LOG_PATH = os.path.join(LOG_DIR, "dns.log")

QTYPE_A = 1
QTYPE_AAAA = 28
QTYPE_HTTPS = 65
QCLASS_IN = 1


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def flipped() -> bool:
    return os.path.exists(FLIP_PATH)


def ghe_ip() -> str:
    return REBIND_IP if flipped() else PUBLIC_IP


def decode_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    jumped = False
    orig = offset
    seen: set[int] = set()
    while True:
        if offset >= len(data):
            raise ValueError("name overflow")
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                raise ValueError("ptr overflow")
            ptr = ((length & 0x3F) << 8) | data[offset + 1]
            if ptr in seen:
                raise ValueError("ptr loop")
            seen.add(ptr)
            if not jumped:
                orig = offset + 2
                jumped = True
            offset = ptr
            continue
        offset += 1
        labels.append(data[offset : offset + length].decode("ascii", "replace"))
        offset += length
    return ".".join(labels).rstrip(".").lower(), (orig if jumped else offset)


def encode_name(name: str) -> bytes:
    out = bytearray()
    cleaned = name.rstrip(".")
    if cleaned:
        for label in cleaned.split("."):
            raw = label.encode("ascii")
            out.append(len(raw))
            out.extend(raw)
    out.append(0)
    return bytes(out)


def parse_query(data: bytes) -> tuple[int, str, int, int] | None:
    if len(data) < 12:
        return None
    txid, flags, qdcount, *_rest = struct.unpack("!HHHHHH", data[:12])
    if qdcount < 1:
        return None
    name, offset = decode_name(data, 12)
    if offset + 4 > len(data):
        return None
    qtype, qclass = struct.unpack("!HH", data[offset : offset + 4])
    return txid, name, qtype, qclass


def build_response(query: bytes, txid: int, qname: str, qtype: int, answers: list[tuple[int, int, bytes]]) -> bytes:
    flags = 0x8400  # QR, AA
    if query[2] & 0x01:
        flags |= 0x0100  # RD
    flags |= 0x0080  # RA
    header = struct.pack("!HHHHHH", txid, flags, 1, len(answers), 0, 0)
    question = encode_name(qname) + struct.pack("!HH", qtype, QCLASS_IN)
    body = bytearray()
    for atype, ttl, rdata in answers:
        body.extend(b"\xc0\x0c")
        body.extend(struct.pack("!HHIH", atype, QCLASS_IN, ttl, len(rdata)))
        body.extend(rdata)
    return header + question + bytes(body)


def is_ghe(qname: str) -> bool:
    return qname == GHE_NAME or qname.endswith("." + GHE_NAME)


def handle_ghe(query: bytes, txid: int, qname: str, qtype: int) -> bytes:
    ip = ghe_ip()
    if qtype == QTYPE_A:
        rdata = socket.inet_aton(ip)
        log(f"A {qname} -> {ip} flip={int(flipped())}")
        return build_response(query, txid, qname, qtype, [(QTYPE_A, 0, rdata)])
    log(f"NODATA {qname} qtype={qtype} flip={int(flipped())}")
    return build_response(query, txid, qname, qtype, [])


def forward(query: bytes) -> bytes | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    try:
        sock.sendto(query, (FORWARDER, 53))
        data, _addr = sock.recvfrom(4096)
        return data
    except OSError as exc:
        log(f"forward-error {exc}")
        return None
    finally:
        sock.close()


def nxdomain(query: bytes, txid: int, qname: str, qtype: int) -> bytes:
    flags = 0x8403
    if query[2] & 0x01:
        flags |= 0x0100
    header = struct.pack("!HHHHHH", txid, flags, 1, 0, 0, 0)
    question = encode_name(qname) + struct.pack("!HH", qtype, QCLASS_IN)
    return header + question


def serve_one(data: bytes, addr, sock: socket.socket) -> None:
    try:
        parsed = parse_query(data)
        if not parsed:
            return
        txid, qname, qtype, qclass = parsed
        if qclass != QCLASS_IN:
            return
        if is_ghe(qname):
            resp = handle_ghe(data, txid, qname, qtype)
        else:
            resp = forward(data)
            if resp is None:
                resp = nxdomain(data, txid, qname, qtype)
                log(f"nxdomain {qname} qtype={qtype}")
            else:
                log(f"forward {qname} qtype={qtype} bytes={len(resp)}")
        sock.sendto(resp, addr)
    except Exception as exc:  # noqa: BLE001
        log(f"handler-error {exc}")


def main() -> None:
    os.makedirs(SHARED_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((BIND, PORT))
    log(f"dns-listen {BIND}:{PORT} ghe={GHE_NAME} public={PUBLIC_IP} rebind={REBIND_IP}")
    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(target=serve_one, args=(data, addr, sock), daemon=True).start()


if __name__ == "__main__":
    main()
