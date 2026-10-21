"""
Build-time tool: regenerates data/logs/access-capture.pcap — a "leaked" packet
capture containing a plaintext HTTP login with the admin creds.

Run from webapps/webapp-a/ :  ../../.venv/bin/python make_capture.py
(scapy is a build-time dependency only; the server doesn't need it)
"""
from scapy.all import Ether, IP, TCP, wrpcap

client_ip, server_ip = "10.13.37.66", "10.13.37.10"
cport, sport = 49152, 80
req = (
    b"POST /login HTTP/1.1\r\n"
    b"Host: 10.13.37.10\r\n"
    b"User-Agent: Mozilla/5.0 (X11; Linux x86_64) Waterfox/115\r\n"
    b"Content-Type: application/x-www-form-urlencoded\r\n"
    b"Content-Length: 39\r\n"
    b"\r\n"
    b"username=admin&password=lil-lizard-123!"
)
resp = (
    b"HTTP/1.1 302 FOUND\r\n"
    b"Location: /dashboard\r\n"
    b"Set-Cookie: session=eyJpZCI6MTIzLCJyb2xlIjoiYWRtaW4iLCJ1c2VybmFtZSI6ImFkbWluIn0.sig\r\n"
    b"\r\n"
)

def pkt(direction, payload, seq, ack, flags):
    if direction == "c2s":
        return Ether() / IP(src=client_ip, dst=server_ip) / TCP(sport=cport, dport=sport, seq=seq, ack=ack, flags=flags) / payload
    return Ether() / IP(src=server_ip, dst=client_ip) / TCP(sport=sport, dport=cport, seq=seq, ack=ack, flags=flags) / payload

capture = [
    pkt("c2s", b"", 1000, 0, "S"),                       # handshake
    pkt("s2c", b"", 5000, 1001, "SA"),
    pkt("c2s", b"", 1001, 5001, "A"),
    pkt("c2s", req, 1001, 5001, "PA"),                   # the login POST
    pkt("s2c", resp, 5001, 1001 + len(req), "A"),        # 302 with session cookie
    pkt("s2c", b"", 5001 + len(resp), 1001 + len(req), "FA"),
    pkt("c2s", b"", 1001 + len(req), 5002 + len(resp), "A"),
]

wrpcap("data/logs/access-capture.pcap", capture)
print("wrote data/logs/access-capture.pcap")
