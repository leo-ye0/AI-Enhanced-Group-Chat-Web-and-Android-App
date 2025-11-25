from llm import chat_completion
from datetime import datetime, timedelta
import json

async def suggest_milestones(chat_history: str, ship_date: str = None, milestone_count: int = 5, project_context: str = "") -> list:
    """
    Use LLM to suggest project milestones based on chat history and ship date.
    
    Returns: [{"title": str, "start_date": str, "end_date": str, "description": str}]
    """
    today = datetime.now().strftime('%Y-%m-%d')
    ship_date_context = f"\nIMPORTANT: Project ship date is {ship_date}. All milestones must end by this date." if ship_date else ""
    
    prompt = f"""Analyze this project conversation and suggest {milestone_count} realistic project milestones with DESCRIPTIVE names.

Chat History:
{chat_history}

{f"Additional Context: {project_context}" if project_context else ""}{ship_date_context}

Generate milestones in JSON format ONLY. Start dates should be realistic based on today's date ({today}).

Output format (JSON array only, no markdown):
[
  {{"title": "Descriptive Phase Name", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "description": "Brief description"}},
  ...
]

Rules:
- Generate exactly {milestone_count} milestones
- Dates must be in YYYY-MM-DD format
- Start dates should be sequential
- Each phase should be 1-4 weeks long
- Titles MUST be descriptive and specific to the project (e.g., "Requirements Gathering", "Backend Development", "User Testing"), NOT generic like "Milestone 1" or "Phase 1"
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
            "title": "Planning",
            "start_date": today.strftime('%Y-%m-%d'),
            "end_date": (today + timedelta(days=phase_days)).strftime('%Y-%m-%d'),
            "description": "Project planning and setup"
        },
        {
            "title": "Development",
            "start_date": (today + timedelta(days=phase_days)).strftime('%Y-%m-%d'),
            "end_date": (today + timedelta(days=phase_days*2)).strftime('%Y-%m-%d'),
            "description": "Core development phase"
        },
        {
            "title": "Testing",
            "start_date": (today + timedelta(days=phase_days*2)).strftime('%Y-%m-%d'),
            "end_date": (datetime.strptime(ship_date, '%Y-%m-%d') if ship_date else today + timedelta(days=phase_days*3)).strftime('%Y-%m-%d'),
            "description": "Testing and quality assurance"
        }
    ]
