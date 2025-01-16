pydhcp
-------

[![PyPI version](https://img.shields.io/pypi/v/pydhcp3?style=for-the-badge)](https://pypi.org/project/pydhcp3/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydhcp3?style=for-the-badge)](https://pypi.org/project/pydhcp3/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://github.com/imgurbot12/pydhcp/blob/master/LICENSE)
[![Made with Love](https://img.shields.io/badge/built%20with-%E2%99%A5-orange?style=for-the-badge)](https://github.com/imgurbot12/pydhcp)

Simple Python DHCP Library. DHCP Packet-Parsing/Client/Server

### Installation

```
pip install pydhcp3
```

### DHCPv4 Examples

Packet Parsing

```python
from pydhcp.v4 import Message

hex = \
    '0101060000003d1d0000000000000000000000000000000000000000000b8201fc4200' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000000000000000000000' +\
    '0000000000000000000000000000000000000000000000000000638253633501013d07' +\
    '01000b8201fc4232040000000037040103062aff00000000000000'

raw     = bytes.fromhex(hex)
message = Message.unpack(raw)
print(message)
```

Client

```python
from pydhcp.v4 import Message
from pydhcp.v4.client import Client, new_message_id

mac    = 'aa:bb:cc:dd:ee:ff'
client = Client(interface=None)

# send crafted messages
id       = new_message_id()
hwaddr   = bytes.fromhex(mac.replace(':', ''))
request  = Message.discover(id, hwaddr)
response = client.request(request)
print(response)

# or simplify the standard network assignment request process
record = client.request_assignment(mac)
print(record)
```

Server

```python
import logging
from ipaddress import IPv4Address, IPv4Network

from pyserve import listen_udp_threaded

from pydhcp.v4.server import Server
from pydhcp.v4.server.backend import MemoryBackend, CacheBackend

# prepare simple memory backend as base provider
backend = MemoryBackend(
    network=IPv4Network('192.168.1.0/24'),
    gateway=IPv4Address('192.168.1.1'),
    dns=[IPv4Address('8.8.8.8'), IPv4Address('8.8.4.4')],
)

# wrap backend w/ cache (not really useful here but for non-memory backends)
backend = CacheBackend(backend)

# configure optional logger for server implementaion
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('myserver')
logger.setLevel(logging.INFO)

# launch server and run forever using pyserve
listen_udp_threaded(
    address=('0.0.0.0', 67),
    factory=Server,
    allow_broadcast=True,
    backend=backend,
    logger=logger,
    server_id=IPv4Address('192.168.1.1') # dhcp server address
)
```
