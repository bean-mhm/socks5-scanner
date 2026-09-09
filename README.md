# SOCKS5 Proxy Scanner

### This project is fully human-crafted and no AI tools were was used.

Here's what `socks5-scanner.py` does when you run it:

1. Read [./socks5-proxy-list-sources.txt](./socks5-proxy-list-sources.txt) which contains a list of
URLs that provide a list of SOCKS5 proxy server addresses in plain text.

2. Fetch the contents of said URLs and parse unique (de-duplicated) addresses
from them. Supported formats: `host:port` in a single line or
`[socks/socks5/socks5h]://host:port` anywhere in a single line. IPv6 addresses
inside curly brackets are also supported. Example: `socks5h://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:1080`

3. For each address, make a GET request to a test URL using said address as a
SOCKS5 proxy and verify the response (can be repeated several times to make sure
it's consistent). The tests are performed asynchronously.

4. Print the list of SOCKS5 proxy servers that pass all tests.

You can adjust different parameters (timeouts, test URL, etc.) by modifying constants at the top of the script.

<details>

<summary><strong>See example output</strong></summary>

```
== found 8 unique sources.

== source 1/8
   https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/protocols/socks5/data.txt
   found 456 new addresses from this source.

== source 2/8
   https://raw.githubusercontent.com/databay-labs/free-proxy-list/refs/heads/master/socks5.txt
   found 243 new addresses from this source (from a total of 328).

== source 3/8
   https://raw.githubusercontent.com/ebrasha/abdal-proxy-hub/refs/heads/main/socks5-proxy-list-by-EbraSha.txt
   found 2113 new addresses from this source (from a total of 2322).

== source 4/8
   https://raw.githubusercontent.com/stormsia/proxy-list/refs/heads/main/socks5.txt
   found 4 new addresses from this source (from a total of 23).

== source 5/8
   https://raw.githubusercontent.com/Vann-Dev/proxy-list/refs/heads/main/proxies/socks5.txt
   found 8 new addresses from this source (from a total of 74).

== source 6/8
   https://raw.githubusercontent.com/VPSLabCloud/VPSLab-Free-Proxy-List/refs/heads/main/socks5_all.txt
   found 144 new addresses from this source (from a total of 409).

== source 7/8
   https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt
   found 39 new addresses from this source (from a total of 243).

== source 8/8
   https://sockslist.us/Raw
   found 69 new addresses from this source (from a total of 100).

== testing 3076 unique addresses
   3076/3076  100.00%   

== 13/3076 SOCKS5 proxies reachable
   fastest response time: 682 ms
   slowest response time: 2661 ms
   addresses are sorted from fastest to slowest.

[OUTPUT]
socks5://45.144.54.40:1080
socks5://157.90.113.23:9052
socks5://83.147.216.208:1080
socks5://87.120.219.126:1082
socks5://45.74.31.30:5397
socks5://147.45.60.139:1082
socks5://108.174.152.80:1080
socks5://107.173.230.93:40000
socks5://5.45.119.70:1080
socks5://18.231.139.246:1080
socks5://47.251.30.12:6000
socks5://144.91.121.61:1088
socks5://193.25.215.182:22222
```

</details>

# Requirements

The [requests](https://requests.readthedocs.io/en/latest/) package must be
installed with the socks dependency
[**(learn more).**](https://requests.readthedocs.io/en/latest/user/advanced/#socks)
Example with pip:

```sh
python -m pip install 'requests[socks]'
```

# Limitations

- Addresses with authentication info are not supported. Example:
`socks5://user:pass@host:port`
