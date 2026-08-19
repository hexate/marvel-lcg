from core import *

class NetLib:

    @staticmethod
    def ListLocalIpAddresses():
        import socket
        ip_addresses: List[str] = []
        hostname = socket.gethostname()  # Get the local machine name
        local_ip = socket.gethostbyname(hostname)  # Get the local IP address
        ip_addresses.append(local_ip)

        # Get all IP addresses associated with the hostname
        for ip in socket.getaddrinfo(hostname, None):
            ip_addresses.append(ip[4][0])

        return sorted(set(ip_addresses))  # Use set to avoid duplicates

    @staticmethod
    def ExtractIpAndPort(input_string: str) -> Tuple[str, int]|None:
        # Updated regex pattern for matching IPv4 and IPv6 addresses with optional port
        import re
        ip_port_pattern = re.compile(r'''
            (?P<ip>
                (?:                             # Non-capturing group for IP
                    (?:\d{1,3}\.){3}\d{1,3}     # IPv4
                    |                           # OR
                    (?:                     # Start of IPv6 with brackets
                        \[?
                        (?:[0-9a-fA-F]{1,4}:    # Start of IPv6
                            (?:                     # Non-capturing group for IPv6
                                [0-9a-fA-F]{0,4}:   # 0-4 hex digits followed by a colon
                            ){0,7}                  # Up to 7 times
                            [0-9a-fA-F]{1,4}        # End with 1-4 hex digits
                        )
                        \]?
                    )                           # End of IPv6 with brackets
                )
            )
            (?::(?P<port>\d{1,5}))?            # Optional port (1-5 digits)
        ''', re.VERBOSE)
        match = ip_port_pattern.search(input_string)  # Use search instead of match
        if match:
            ip = match.group('ip')
            port_str = match.group('port')
            if port_str is not None:
                port = int(port_str)
                if 0 <= port <= 65535:  # Validate port range
                    return (ip, port)
        return None

    @staticmethod
    def WhyPortUnavailable(address: str, port: int) -> str|None:
        """None if the server could bind here, otherwise why it could not. J14.

        The point of this probe is to predict whether the real bind will succeed, and it used to
        get that wrong in the one case that matters. `asyncio.create_server`, which is what
        actually opens the socket, sets `SO_REUSEADDR` on POSIX by default. This probe did not, so
        it was stricter than the bind it was standing in for: a port left in `TIME_WAIT` by a
        browser that still had keep-alive connections open would be refused here even though the
        server itself would have taken it happily.

        The effect was that quitting the game and starting it again inside that window died on an
        assertion, with no listener anywhere in `netstat`, and the only cure was to close the tab
        or wait the timeout out. Matching the flag makes the probe agree with reality.

        The old bare `except` also swallowed everything, including a bad address, and reported all
        of it as "port taken". Only `OSError` means the port is unusable.
        """
        import socket

        family = socket.AF_INET6 if ':' in address else socket.AF_INET
        s = socket.socket(family, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((address, port))
            return None
        except OSError as exc:
            # errno is the useful part: EADDRINUSE means something is listening, EADDRNOTAVAIL
            # means the address is not ours to bind, and they need different fixes.
            return f"{exc.strerror or exc} (errno {exc.errno})"
        finally:
            s.close()

    @staticmethod
    def IsPortAvailable(address: str, port: int) -> bool:
        return NetLib.WhyPortUnavailable(address, port) is None

