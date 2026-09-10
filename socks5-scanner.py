import time
import requests
import asyncio
from pathlib import Path
from copy import deepcopy

from common import *


SOURCES_PATH = Path("./socks5-proxy-list-sources.txt")
"""
path to a text file containing a list of URLs that provide a list of SOCKS5
proxy server addresses in plain text.
"""


SOURCE_REQ_HEADERS: dict = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:155.0) Gecko/20100101 Firefox/155.0",
    "Accept": "text/plain,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
}
SOURCE_REQ_VERIFY_SSL: bool = True
SOURCE_REQ_TIMEOUT: float = 5.

# https://requests.readthedocs.io/en/latest/user/advanced/#proxies
SOURCE_REQ_PROXIES: dict[str, str] | None = None


TEST_URL: str = "https://www.youtube.com/t/contact_us/"
TEST_EXPECTED_STATUS_CODES: list[int] = [200]
TEST_REQ_HEADERS: dict = deepcopy(SOURCE_REQ_HEADERS)
TEST_REQ_TIMEOUT: float = 5.
TEST_REQ_VERIFY_SSL: bool = True

N_TEST_ITERS: int = 3
"""
how many times a SOCKS5 proxy address needs to pass the test to be considered
reachable.
"""

TEST_COOLDOWN: float = 3.
"""
time delay in seconds between every iteration of a test. for example, if
N_TEST_ITERS is 3, we will wait TEST_COOLDOWN seconds after the first and second
iterations.
"""

TEST_N_CONCURRENT_REQS: int = 32
"maximum number of test requests in progress at a time"


OUTPUT_FORMAT: str = "socks://{0}"
"argument #0 is address (host:port), #1 is response time in milliseconds."


test_reqs_semaphore = asyncio.Semaphore(TEST_N_CONCURRENT_REQS)


def is_valid_port(s: str) -> bool:
    try:
        i = int(s)
        return i in range(65536) and str(i) == s
    except Exception:
        return False


def is_basic_address(s: str) -> bool:
    "returns True if given string is a basic hostname:port address"
    if len(s) < 3:
        return False
    colon_split = s.rsplit(":", 1)
    return len(colon_split) == 2 and is_valid_port(colon_split[1]) \
        and "://" not in colon_split[0]


def parse_socks5_addresses(address_list_str: str) -> list[str]:
    addresses: list[str] = []
    lines = address_list_str.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if is_basic_address(line):
            addresses.append(line)
            continue

        KEYWORD: str = "socks"
        start: int = 0
        while True:
            start = line.find(KEYWORD, start)
            if start < 0:
                break

            start += len(KEYWORD)

            if len(line) < start + 6:
                break

            if line[start:start + 3] == "://":
                start += 3
            elif line[start:start + 4] == "5://":
                start += 4
            elif line[start:start + 5] == "5h://":
                start += 5
            else:
                continue

            if len(line) < start + 3:
                break

            port_start: int = -1
            if line[start] == '[':
                # handle IPv6 addresses like [1fff:0:a88:85a3::ac1f]:1080
                MAX_IPV6_LEN: int = 39
                for i in range(1, MAX_IPV6_LEN + 2):
                    if start + i + 2 >= len(line):
                        break
                    if line[start + i:start + i + 2] == "]:":
                        port_start = start + i + 2
            else:
                MAX_HOST_LEN: int = 500
                for i in range(1, MAX_HOST_LEN + 1):
                    if start + i + 1 >= len(line):
                        break
                    if line[start + i] == ":":
                        port_start = start + i + 1

            if port_start < 0:
                continue

            end: int = -1
            MAX_PORT_LEN: int = 5
            for i in range(1, MAX_PORT_LEN + 1):
                if len(line) < port_start + i:
                    break
                if is_valid_port(line[port_start:port_start + i]):
                    end = port_start + i
            if end < 0:
                continue

            addresses.append(line[start:end])

    # remove duplicates and return
    return unique(addresses)


def test_socks5_address(address: str) -> float | None:
    """
    returns the response time in seconds, or None if failed.
    """
    try:
        start_time = time.time()
        response = requests.get(
            TEST_URL,
            headers=TEST_REQ_HEADERS,
            timeout=TEST_REQ_TIMEOUT,
            allow_redirects=True,
            proxies={
                "http": f"socks5h://{address}",
                "https": f"socks5h://{address}"
            },
            verify=TEST_REQ_VERIFY_SSL
        )
        if response.status_code not in TEST_EXPECTED_STATUS_CODES:
            raise Exception(
                f"unexpected status code ({response.status_code})"
            )
        return time.time() - start_time
    except Exception as e:
        root_log.debug(
            f"address \"{address}\" failed test: {format_exception(e)}"
        )
        return None


socks5_concurrent_test_n_done: int = 0


def socks5_concurrent_test_print_progress_and_increment(n_total: int):
    global socks5_concurrent_test_n_done

    n_done = socks5_concurrent_test_n_done + 1
    socks5_concurrent_test_n_done += 1
    print(
        f"\r   {n_done}/{n_total}  {n_done / n_total * 100:.2f}%",
        end=""
    )


async def test_socks5_address_concurrent(
    address: str,
    n_total: int
) -> tuple[str, float] | None:
    """
    returns a tuple containing the address and its average response time in
    seconds, or None if failed.
    """

    global socks5_concurrent_test_n_done

    total_response_time: float = 0.
    for test_iter in range(N_TEST_ITERS):
        async with test_reqs_semaphore:
            response_time = await asyncio.to_thread(
                test_socks5_address,
                address
            )
        if response_time is None:
            socks5_concurrent_test_print_progress_and_increment(n_total)
            return None
        total_response_time += response_time

        if test_iter < N_TEST_ITERS - 1:
            await asyncio.sleep(TEST_COOLDOWN)

    socks5_concurrent_test_print_progress_and_increment(n_total)
    return (address, total_response_time / float(N_TEST_ITERS))


async def test_socks5_addresses_concurrent(
    addresses: list[str]
) -> list[tuple[str, float]]:
    global socks5_concurrent_test_n_done
    socks5_concurrent_test_n_done = 0

    print(" " * 24, end="")
    tasks = [
        test_socks5_address_concurrent(
            address,
            len(addresses)
        )
        for address in addresses
    ]
    results = await asyncio.gather(*tasks)
    print("")

    # keep successful results
    reachable = [r for r in results if r is not None]

    # sort by response time (2nd element of the tuple)
    reachable.sort(key=lambda item: item[1])
    return reachable


def main():
    sources = []
    try:
        sources = SOURCES_PATH.read_text().splitlines()
        sources = list(filter(
            lambda v: v and not v.startswith("#") and "://" in v,
            sources
        ))
        sources = unique(sources)
    except Exception:
        pass

    if not sources:
        print(
            f"there are no sources. make sure \"{SOURCES_PATH}\" exists and "
            f"contains a list of source URLs that provide SOCKS5 proxy lists "
            f"in plain text."
        )
        exit(1)
    print(f"== found {len(sources)} unique sources.")

    all_addresses: list[str] = []
    for idx, source in enumerate(sources):
        print(
            f"\n== source {idx + 1}/{len(sources)}\n"
            f"   {source}"
        )

        # fetch URL content
        try:
            response = requests.get(
                source,
                headers=SOURCE_REQ_HEADERS,
                timeout=SOURCE_REQ_TIMEOUT,
                allow_redirects=True,
                proxies=SOURCE_REQ_PROXIES,
                verify=SOURCE_REQ_VERIFY_SSL
            )
            response.raise_for_status()
            response = response.text
        except Exception as e:
            root_log.error(
                f"   source is unreachable: {format_exception(e)}"
            )
            continue

        # parse addresses
        addresses = parse_socks5_addresses(response)
        n_all_addresses = len(addresses)

        # only keep new addresses that we haven't seen before
        addresses = list(filter(
            lambda v: v not in all_addresses,
            addresses
        ))
        all_addresses.extend(addresses)

        print(
            f"   found {len(addresses)} new addresses from this source",
            end=""
        )
        if n_all_addresses > len(addresses):
            print(f" (from a total of {n_all_addresses})", end="")
        print(".")

    if not all_addresses:
        print("== no addresses found.")
        return

    print(f"\n== testing {len(all_addresses)} unique addresses")

    # test addresses concurrently
    reachable = asyncio.run(
        test_socks5_addresses_concurrent(all_addresses)
    )

    # print the results
    if reachable:
        reachable_addresses = [
            OUTPUT_FORMAT.format(addr, int(resp_time * 1000.))
            for addr, resp_time in reachable
        ]
        resp_times = [resp_time for addr, resp_time in reachable]
        fastest_ms = int(resp_times[0] * 1000.)
        slowest_ms = int(resp_times[-1] * 1000.)

        print(
            f"\n== {len(reachable)}/{len(all_addresses)} SOCKS5 proxies "
            f"reachable\n"
            f"   fastest response time: {fastest_ms} ms\n"
            f"   slowest response time: {slowest_ms} ms\n"
            f"   addresses are sorted from fastest to slowest.\n\n"
            f"[OUTPUT]"
        )
        print("\n".join(reachable_addresses))
    else:
        print(
            f"\n==no reachable SOCKS5 proxies out of {len(all_addresses)}\n\n"
            f"[OUTPUT]"
        )


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        root_log.fatal(format_exception(e))
        exit(1)
