import os
import subprocess
import asyncio
import json
import shodan
from censys.search import CensysHosts
from greynoise import GreyNoise
from typing import List, Dict

class ScoutAgent:
    def __init__(self):
        self.shodan_api = shodan.Shodan(os.getenv("SHODAN_API_KEY"))
        self.censys_id = os.getenv("CENSYS_ID")
        self.censys_secret = os.getenv("CENSYS_SECRET")
        self.chaos_key = os.getenv("PDCP_API_KEY") # Chaos uses ProjectDiscovery Cloud Key
        self.gn_client = GreyNoise(api_key=os.getenv("GREYNOISE_API_KEY"))

    # --- 1. PASSIVE INTEL (The Silent Phase) ---
    async def get_chaos_subdomains(self, domain: str) -> List[str]:
        """Fetch pre-indexed subdomains from Chaos DB."""
        print(f"[*] Querying Chaos DB for {domain}...")
        try:
            cmd = ["chaos", "-d", domain, "-key", self.chaos_key, "-silent"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.splitlines()
        except Exception as e:
            print(f"[!] Chaos Error: {e}")
            return []

    def get_shodan_intel(self, domain: str) -> List[Dict]:
        """Instant port/service lookup via Shodan."""
        print(f"[*] Pulling Shodan Intel for {domain}...")
        try:
            # Search for assets associated with the hostname
            query = f"hostname:{domain}"
            results = self.shodan_api.search(query)
            return [{"ip": r['ip_str'], "port": r['port'], "svc": r.get('product', 'unknown')} 
                    for r in results['matches']]
        except Exception as e:
            print(f"[!] Shodan Error: {e}")
            return []

    def check_greynoise(self, ip_list: List[str]):
        """Filter out 'Internet Noise' and HoneyPots."""
        # GreyNoise helps prevent the swarm from attacking known research scanners
        noise_results = self.gn_client.quick_check(ip_list)
        return [res for res in noise_results if not res['noise']]

    # --- 2. ACTIVE RECON (The Probing Phase) ---
    async def run_subfinder(self, domain: str) -> List[str]:
        """Active subdomain brute-forcing and API scraping."""
        print(f"[*] Launching Subfinder on {domain}...")
        cmd = ["subfinder", "-d", domain, "-silent"]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = await proc.communicate()
        return stdout.decode().splitlines()

    async def verify_alive(self, subdomains: List[str]) -> List[Dict]:
        """HTTPX: Identify which subdomains are actually live web servers."""
        print(f"[*] Verifying {len(subdomains)} subdomains with HTTPX...")
        # We pipe subdomains into httpx via stdin for maximum speed
        sub_input = "\n".join(subdomains).encode()
        cmd = ["httpx", "-silent", "-json", "-title", "-tech-detect", "-status-code"]
        proc = await asyncio.create_subprocess_exec(*cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, _ = await proc.communicate(input=sub_input)
        
        results = []
        for line in stdout.decode().splitlines():
            if line:
                results.append(json.loads(line))
        return results

    # --- 3. DEEP AUDIT (The Heavy Hitters) ---
    async def run_vulnhuntr(self, repo_path: str):
        """Invoke the Python 3.10 VulnHuntr engine."""
        print(f"[*] Initiating Deep AI Audit on {repo_path}...")
        # Use the isolated 3.10 environment we built in the Dockerfile
        cmd = ["/opt/vulnhuntr_env/bin/vulnhuntr", "-r", repo_path]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        return stdout.decode()

    async def run_nuclei(self, target_url: str):
        """Scan for specific CVEs and misconfigurations."""
        print(f"[*] Running Nuclei templates against {target_url}...")
        cmd = ["nuclei", "-u", target_url, "-silent", "-severity", "high,critical", "-json"]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE)
        stdout, _ = await proc.communicate()
        return [json.loads(line) for line in stdout.decode().splitlines() if line]