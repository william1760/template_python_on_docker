import dns.resolver
import dns.exception
import requests
import logging
import time
import argparse
import validators


class DNS_Resolver:
    @staticmethod
    def resolve_ip(host='github.com', dns_srv='1.1.1.1'):
        dns_resolver = dns.resolver.Resolver(configure=False)
        dns_resolver.cache = dns.resolver.Cache()
        dns_resolver.lifetime = 5  # Timeout for the entire query
        dns_resolver.timeout = 2   # Timeout per server

        # Validate DNS server and host
        if not dns.inet.is_address(dns_srv):
            logging.error(f"[DNS_Resolver] Invalid DNS server: {dns_srv}")
            return []

        if not validators.domain(host):
            logging.error(f"[DNS_Resolver] Invalid host: {host}")
            return []

        # Use only the specified DNS server for the query
        dns_resolver.nameservers = [dns_srv]

        try:
            dns.resolver.override_system_resolver(dns_resolver)
            start_time = time.time()
            answer = dns_resolver.resolve(host, 'A')
            end_time = time.time()

            ip_array = [str(ip) for ip in answer]
            response_time = (end_time - start_time) * 1000  # in ms

            logging.info(f"[DNS_Resolver] Resolved {host} in {response_time:.2f} ms via {dns_srv}: {', '.join(ip_array)}")
            return ip_array

        except dns.resolver.NXDOMAIN:
            logging.warning(f"[DNS_Resolver] {host} does not exist.")
            return []

        except dns.resolver.Timeout:
            logging.warning(f"[DNS_Resolver] {dns_srv} timed out for {host}.")
            return []

        except dns.exception.DNSException as e:
            logging.error(f"[DNS_Resolver] DNS error for {host} via {dns_srv}: {e}")
            return []

        finally:
            dns.resolver.restore_system_resolver()

    @staticmethod
    def get_current_ip(resolvers):
        if not isinstance(resolvers, list) or not resolvers:
            logging.error("[get_current_ip] Resolvers must be a non-empty list of URLs.")
            return None

        ip_results = []

        for url in resolvers:
            if not validators.url(url):
                logging.error(f"[get_current_ip] Invalid URL: {url}")
                continue

            try:
                # Make a secure GET request with timeout
                start_time = time.time()
                response = requests.get(url, timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000  # in ms

                # Check for successful status code
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        logging.error(f"[get_current_ip] Invalid JSON response from: {url}")
                        continue

                    # Validate the JSON structure
                    if 'ip' not in data:
                        logging.error(f"[get_current_ip] Missing 'ip' field in response from: {url}")
                        continue

                    public_ip = data['ip']
                    logging.info(f"[get_current_ip] Retrieved IP: {public_ip} in {response_time:.2f} ms from {url}")
                    ip_results.append(public_ip)
                else:
                    logging.error(
                        f"[get_current_ip] Failed to retrieve IP. Status code: {response.status_code} from {url}")

            except requests.Timeout:
                logging.error(f"[get_current_ip] Request timed out for: {url}")
            except requests.exceptions.SSLError:
                logging.warning(f"[get_current_ip] {url} has an invalid SSL certificate")
            except requests.RequestException as e:
                logging.error(f"[get_current_ip] An error occurred: {e}")

        # Check for consistency in IP results
        if ip_results:
            if len(set(ip_results)) == 1 and len(ip_results) == len(resolvers):
                consistent_ip = ip_results[0]
                logging.info(f"[get_current_ip] All resolvers returned consistent IP: {consistent_ip}")
                return consistent_ip
            else:
                logging.error(f"[get_current_ip] Inconsistent results from resolvers: {ip_results} ({len(ip_results)} /"
                              f" {len(resolvers)})")
                return None
        else:
            logging.error("[get_current_ip] No valid responses from any resolvers.")
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolve a domain to its IP address using a specific DNS server.")
    parser.add_argument("--host", default="github.com", help="Domain to resolve (default: github.com)")
    parser.add_argument("--dns_server", default="1.1.1.1", help="DNS server to use (default: 1.1.1.1)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    resolver = [
        "https://myipv4.p1.opendns.com/get_my_ip",
        "https://api.iplocation.net/?cmd=get-ip",
        "https://ipinfo.io/json"]

    # Configure logging
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    result = DNS_Resolver.resolve_ip(args.host, args.dns_server)
    if result:
        print(f"Resolved IPs for {args.host} via {args.dns_server}: {', '.join(result)}")
    else:
        print(f"Failed to resolve {args.host} via {args.dns_server}. Check logs for details.")

    current_ip = DNS_Resolver.get_current_ip(resolver)
    if current_ip:
        print(f"Public IP: {current_ip}")
    else:
        print("Failed to determine public IP.")