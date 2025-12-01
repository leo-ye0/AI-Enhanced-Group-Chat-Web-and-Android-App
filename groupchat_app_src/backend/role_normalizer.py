from llm import chat_completion
import json
import asyncio

async def normalize_role(user_input: str) -> str:
    """Use LLM to normalize role titles and understand synonyms. Supports multiple comma-separated roles."""
    # Split by comma or newline to handle multiple roles
    roles = [r.strip() for r in user_input.replace('\n', ',').split(',') if r.strip()]
    
    if len(roles) == 0:
        return user_input
    
    # Normalize each role individually
    normalized_roles = []
    for role in roles:
        prompt = f"""Normalize this job title/role into a clear, standard category.

User input: "{role}"

Return ONLY a JSON object:
{{"normalized_role": "Standard Role Name"}}

Rules:
- Identify the core profession/role
- Normalize synonyms and abbreviations to standard terms
- Examples:
  * "SWE", "SDE", "software eng" → "Software Developer"
  * "RN", "registered nurse" → "Nurse"
  * "teacher", "educator", "instructor" → "Teacher"
  * "accountant", "CPA" → "Accountant"
  * "sales rep", "account exec" → "Sales Representative"
  * "marketing specialist", "marketer" → "Marketing Specialist"
- Keep it concise (2-3 words max)
- Use title case
- Work for ANY profession (tech, medical, education, business, trades, etc.)
"""
        
        try:
            response = await chat_completion([{"role": "user", "content": prompt}])
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                normalized_roles.append(result.get("normalized_role", role))
            else:
                normalized_roles.append(role)
        except:
            normalized_roles.append(role)
    
    return ', '.join(normalized_roles)
