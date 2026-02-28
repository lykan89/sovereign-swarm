import os
import json
import asyncio
from typing import Annotated, TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

# Import our custom agents (enabled by your __init__.py)
from agents import ScoutAgent, SwarmCommander, AuditorAgent

load_dotenv()

# 1. Define the Shared State
# This is the "Data Bus" that flows between agents.
class SwarmState(TypedDict):
    target_domain: str
    recon_data: Dict          # Found subdomains, IPs, and open ports
    mission_plan: Dict       # The DeepSeek-R1 Strategic Plan
    final_findings: List[Dict] # Confirmed vulnerabilities

# 2. Initialize the Agents
scout = ScoutAgent()
commander = SwarmCommander()
auditor = AuditorAgent()

# --- Node Functions ---

async def scout_node(state: SwarmState):
    """The Intelligence Phase."""
    target = state["target_domain"]
    print(f"\n[>>>] NODE: SCOUT | Target: {target}")
    
    # Run passive and active recon in parallel
    chaos_task = scout.get_chaos_subdomains(target)
    subfinder_task = scout.run_subfinder(target)
    
    chaos_subs, subfinder_subs = await asyncio.gather(chaos_task, subfinder_task)
    all_subs = list(set(chaos_subs + subfinder_subs))
    
    # Filter for live services
    live_services = await scout.verify_alive(all_subs)
    shodan_data = scout.get_shodan_intel(target)
    
    return {
        "recon_data": {
            "subdomains": all_subs,
            "live_services": live_services,
            "shodan": shodan_data
        }
    }

async def commander_node(state: SwarmState):
    """The Strategic Phase (DeepSeek-R1)."""
    print(f"\n[>>>] NODE: COMMANDER | Reasoning about attack vectors...")
    
    plan_raw = await commander.analyze_and_plan(
        state["target_domain"], 
        state["recon_data"]
    )
    
    # Extract JSON if R1 wraps it in markdown blocks
    clean_plan = plan_raw.strip("`json").strip("`").strip()
    return {"mission_plan": json.loads(clean_plan)}

async def auditor_node(state: SwarmState):
    """The Execution Phase."""
    print(f"\n[>>>] NODE: AUDITOR | Executing deep audits...")
    
    results = await auditor.process_commander_plan(state["mission_plan"])
    
    # Save findings to the Docker volume (/app/results)
    output_path = f"/app/results/final_report_{state['target_domain']}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"[+] Mission Complete. Report saved to: {output_path}")
    return {"final_findings": results}

# 3. Build the Graph
workflow = StateGraph(SwarmState)

# Add our specialized nodes
workflow.add_node("scout", scout_node)
workflow.add_node("commander", commander_node)
workflow.add_node("auditor", auditor_node)

# Define the flow: Scout -> Commander -> Auditor -> End
workflow.add_edge(START, "scout")
workflow.add_edge("scout", "commander")
workflow.add_edge("commander", "auditor")
workflow.add_edge("auditor", END)

# 4. Compile and Run
app = workflow.compile()

async def run_swarm(domain: str):
    initial_state = {
        "target_domain": domain,
        "recon_data": {},
        "mission_plan": {},
        "final_findings": []
    }
    await app.ainvoke(initial_state)

if __name__ == "__main__":
    target = input("Enter target domain (e.g., example.com): ")
    asyncio.run(run_swarm(target))