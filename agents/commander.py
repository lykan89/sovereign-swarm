import os
from typing import List, Dict
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage
from .scout import ScoutAgent

class SwarmCommander:
    def __init__(self):
        # We use the 'deepseek-reasoner' model (R1) for high-level strategy
        self.llm = ChatDeepSeek(
            model="deepseek-reasoner",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0  # Hard logic, no "creative" halluctions
        )
        self.scout = ScoutAgent()

    async def analyze_and_plan(self, target_domain: str, recon_data: Dict):
        """
        The Core Reasoning Loop:
        1. Review all 'Intel' (Shodan, Chaos, Httpx).
        2. Identify the 'Crown Jewels' (Admin panels, API endpoints, Git folders).
        3. Assign specific tools (Nuclei, VulnHuntr, SQLMap) to targets.
        """
        
        # Prepare the context for the R1 Brain
        context = f"""
        TARGET: {target_domain}
        SUBDOMAINS_FOUND: {len(recon_data.get('subdomains', []))}
        LIVE_HTTP_SERVICES: {json.dumps(recon_data.get('http_results', []), indent=2)}
        SHODAN_INTEL: {json.dumps(recon_data.get('shodan_intel', []), indent=2)}
        """

        system_prompt = """
        You are the Sovereign Swarm Commander. Your goal is to identify the most vulnerable entry point.
        Analyze the provided recon data. Look for:
        1. Outdated tech stacks (PHP 5.x, Old IIS).
        2. Interesting endpoints (/api/v1, /admin, /.git, /debug).
        3. Exposed services on non-standard ports (8080, 8443, 5000).
        
        Return a JSON plan:
        {
          "high_priority_targets": ["url1", "url2"],
          "strategy": "Reasoning for choosing these",
          "tool_assignment": [{"target": "url1", "tool": "vulnhuntr"}, {"target": "url2", "tool": "nuclei"}]
        }
        """

        print(f"[*] Commander R1 is analyzing {target_domain} strategy...")
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ])

        # DeepSeek-R1 returns 'thought' process + 'content'
        # content will be our JSON plan
        return response.content

    async def execute_mission(self, target_domain: str):
        """The main entry point for a target."""
        
        # Phase 1: Passive Intelligence
        chaos_subs = await self.scout.get_chaos_subdomains(target_domain)
        shodan_intel = self.scout.get_shodan_intel(target_domain)
        
        # Phase 2: Active Verification
        subfinder_subs = await self.scout.run_subfinder(target_domain)
        all_subs = list(set(chaos_subs + subfinder_subs))
        
        live_services = await self.scout.verify_alive(all_subs)
        
        # Phase 3: Strategic Planning (The AI Part)
        recon_summary = {
            "subdomains": all_subs,
            "http_results": live_services,
            "shodan_intel": shodan_intel
        }
        
        plan = await self.analyze_and_plan(target_domain, recon_summary)
        print(f"\n[!] SWARM MISSION PLAN:\n{plan}\n")
        
        return plan