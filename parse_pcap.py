import struct
import sys

PCAP_FILE = r"c:\Users\DELL\Projects\Resume AI by ThetaLogics\Logs\call-log-CA70f8d0d41333933e621020fe709db445 (1).pcap"

def parse_pcap(path):
    with open(path, "rb") as f:
        data = f.read()

    magic = struct.unpack("<I", data[:4])[0]
    if magic == 0xA1B2C3D4:
        endian = "<"
    elif magic == 0xD4C3B2A1:
        endian = ">"
    else:
        print(f"Unknown PCAP magic: {hex(magic)}")
        return

    header = struct.unpack(endian + "IHHIIII", data[:24])
    snaplen, linktype = header[5], header[6]
    print(f"Magic: {hex(magic)}, Snaplen: {snaplen}, LinkType: {linktype}")

    offset = 24
    pkt_num = 0
    while offset < len(data):
        pkt_num += 1
        ph = struct.unpack(endian + "IIII", data[offset:offset+16])
        ts_sec, ts_usec, incl_len, orig_len = ph
        offset += 16
        pkt = data[offset:offset+incl_len]
        offset += incl_len

        if linktype == 1:  # Ethernet
            eth_type = struct.unpack("!H", pkt[12:14])[0]
            ip_start = 14
        elif linktype == 101:  # Raw IP
            eth_type = 0x0800
            ip_start = 0
        elif linktype == 113:  # Linux cooked capture (SLL)
            eth_type = struct.unpack("!H", pkt[14:16])[0]
            ip_start = 16
        else:
            print(f"[skip packet {pkt_num}] unsupported link type {linktype}")
            continue

        if eth_type != 0x0800:
            continue

        ip = pkt[ip_start:]
        ihl = (ip[0] & 0x0F) * 4
        proto = ip[9]
        src_ip = ".".join(str(b) for b in ip[12:16])
        dst_ip = ".".join(str(b) for b in ip[16:20])

        transport = ip[ihl:]
        if proto == 17:  # UDP
            src_port, dst_port = struct.unpack("!HH", transport[:4])
            if src_port == 5060 or dst_port == 5060:
                payload = transport[8:]
                try:
                    text = payload.decode("utf-8", errors="replace")
                except Exception:
                    text = payload.decode("latin-1", errors="replace")
                print(f"\n=== Packet {pkt_num} UDP {src_ip}:{src_port} -> {dst_ip}:{dst_port} ===")
                print(text[:2000])
        elif proto == 6:  # TCP
            src_port, dst_port = struct.unpack("!HH", transport[:4])
            if src_port == 5060 or dst_port == 5060:
                payload = transport[20:]
                try:
                    text = payload.decode("utf-8", errors="replace")
                except Exception:
                    text = payload.decode("latin-1", errors="replace")
                print(f"\n=== Packet {pkt_num} TCP {src_ip}:{src_port} -> {dst_ip}:{dst_port} len={len(payload)} ===")
                print(text[:2000])

if __name__ == "__main__":
    parse_pcap(PCAP_FILE)
