from datetime import datetime, date
from typing import List, Dict, Any

def calculate_project_pulse(current_date: str, milestones: List[Dict], tasks: List[Dict]) -> Dict[str, Any]:
    """
    Calculate project pulse status for all milestones.
    
    Args:
        current_date: YYYY-MM-DD format
        milestones: [{"title": str, "start_date": str, "end_date": str}]
        tasks: [{"milestone": str, "status": "pending"|"completed"}]
    
    Returns:
        JSON object with phases array containing status for each milestone
    """
    curr = datetime.strptime(current_date, "%Y-%m-%d").date()
    
    phases = []
    for m in milestones:
        start = datetime.strptime(m["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(m["end_date"], "%Y-%m-%d").date()
        
        # Calculate progress
        phase_tasks = [t for t in tasks if t.get("milestone") == m["title"]]
        total = len(phase_tasks)
        completed = len([t for t in phase_tasks if t.get("status") == "completed"])
        progress = round((completed / total * 100) if total > 0 else 0)
        
        # Calculate deadline delta
        days_remaining = (end - curr).days
        
        # Determine status
        if curr < start:
            status = "UPCOMING"
        elif curr > end:
            status = "COMPLETED"
        else:
            status = "ACTIVE"
        
        # Determine urgency for active phases
        if status == "ACTIVE":
            if days_remaining < 3:
                urgency = "CRITICAL"
            elif days_remaining < 7:
                urgency = "WARNING"
            else:
                urgency = "ON_TRACK"
        else:
            urgency = "ON_TRACK"
        
        phases.append({
            "title": m["title"],
            "progress": progress,
            "days_remaining": days_remaining,
            "status": status,
            "urgency": urgency
        })
    
    return {"phases": phases}
