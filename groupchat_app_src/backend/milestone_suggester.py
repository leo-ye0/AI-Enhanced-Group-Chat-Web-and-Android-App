from llm import chat_completion
from datetime import datetime, timedelta
import json
from typing import Optional, List, Dict
from vector_db import search_documents

async def suggest_milestones(chat_history: str, ship_date: str = None, milestone_count: int = 5, project_context: str = "", team_roles: Optional[List[str]] = None) -> list:
    """
    Enhanced milestone suggestion with RAG, team capacity, and risk assessment.
    
    Returns: [{"title": str, "start_date": str, "end_date": str, "description": str, "assigned_roles": str, "risk_level": str}]
    """
    today = datetime.now().strftime('%Y-%m-%d')
    ship_date_context = f"\nIMPORTANT: Project ship date is {ship_date}. All milestones must end by this date." if ship_date else ""
    
    # Extract requirements from uploaded documents using RAG
    rag_context = ""
    try:
        search_results = search_documents("project requirements specifications timeline deliverables", n_results=3)
        if search_results['documents'] and search_results['documents'][0]:
            docs = [doc for docs in search_results['documents'] for doc in docs if doc]
            rag_context = f"\n\nExtracted Requirements from Documents:\n{' '.join(docs[:2])[:1000]}"
    except:
        pass
    
    # Team capacity context
    team_context = f"\n\nTeam Roles Available: {', '.join(team_roles)}" if team_roles else ""
    
    prompt = f"""Analyze this project and suggest {milestone_count} realistic milestones with risk assessment and resource allocation.

Chat History:
{chat_history}

{f"Additional Context: {project_context}" if project_context else ""}{ship_date_context}{rag_context}{team_context}

Generate milestones in JSON format ONLY. Consider:
1. Working days (skip weekends)
2. Team capacity and roles
3. Dependencies between phases
4. Risk factors (complexity, unknowns)
5. Buffer time for high-risk phases

Today's date: {today}

Output format (JSON array only, no markdown):
[
  {{
    "title": "Descriptive Phase Name",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "description": "What will be accomplished",
    "assigned_roles": "Roles needed (e.g., Backend Dev, Designer)",
    "risk_level": "low/medium/high",
    "dependencies": "Previous milestone titles this depends on"
  }}
]

Rules:
- Generate exactly {milestone_count} milestones
- Dates in YYYY-MM-DD format, skip weekends
- Sequential start dates with realistic durations (1-4 weeks)
- Descriptive titles specific to project (NOT "Milestone 1")
- Assign roles based on team composition
- Mark high-risk phases (new tech, complex features)
{f"- Final milestone must end on or before {ship_date}" if ship_date else ""}
"""
    
    response = await chat_completion([{"role": "user", "content": prompt}])
    
    try:
        # Extract JSON from response
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response[json_start:json_end]
            milestones = json.loads(json_str)
            # Ensure all milestones have required fields
            for m in milestones:
                m.setdefault('assigned_roles', 'Team')
                m.setdefault('risk_level', 'medium')
                m.setdefault('dependencies', 'None')
            return milestones
        else:
            # Fallback: generate default milestones
            return generate_default_milestones(ship_date)
    except:
        return generate_default_milestones(ship_date)

def generate_default_milestones(ship_date: str = None):
    """Generate default milestones if LLM fails."""
    today = datetime.now()
    if ship_date:
        end = datetime.strptime(ship_date, '%Y-%m-%d')
        total_days = (end - today).days
        phase_days = max(7, total_days // 3)
    else:
        phase_days = 7
    
    return [
        {
            "title": "Planning & Requirements",
            "start_date": today.strftime('%Y-%m-%d'),
            "end_date": (today + timedelta(days=phase_days)).strftime('%Y-%m-%d'),
            "description": "Project planning and requirements gathering",
            "assigned_roles": "PM, Team Lead",
            "risk_level": "low",
            "dependencies": "None"
        },
        {
            "title": "Development",
            "start_date": (today + timedelta(days=phase_days)).strftime('%Y-%m-%d'),
            "end_date": (today + timedelta(days=phase_days*2)).strftime('%Y-%m-%d'),
            "description": "Core development and implementation",
            "assigned_roles": "Developers, Designers",
            "risk_level": "medium",
            "dependencies": "Planning & Requirements"
        },
        {
            "title": "Testing & Launch",
            "start_date": (today + timedelta(days=phase_days*2)).strftime('%Y-%m-%d'),
            "end_date": (datetime.strptime(ship_date, '%Y-%m-%d') if ship_date else today + timedelta(days=phase_days*3)).strftime('%Y-%m-%d'),
            "description": "Testing, bug fixes, and deployment",
            "assigned_roles": "QA, DevOps, Team",
            "risk_level": "high",
            "dependencies": "Development"
        }
    ]
