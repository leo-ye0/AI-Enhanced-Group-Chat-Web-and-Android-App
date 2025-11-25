"""
Dialectic Engine: AI-powered conflict detection and Socratic decision-making system.

This module implements:
1. Silent monitoring of conversations for factual conflicts
2. RAG-based evidence retrieval from uploaded documents
3. Socratic intervention with structured decision options
4. Team voting system with 24-hour consensus periods
5. Decision logging for project audit trails
"""

from typing import Dict, List, Optional
from vector_db import search_documents
from llm import chat_completion

class ConflictDetector:
    """Detects conflicts between user statements and uploaded document evidence."""
    
    @staticmethod
    async def check_for_conflicts(user_statement: str) -> Optional[Dict]:
        """Check if user statement conflicts with uploaded documents."""
        # Skip if not project-relevant
        is_relevant = await ConflictDetector._is_project_relevant(user_statement)
        if not is_relevant:
            return None
        
        # Skip questions but allow vote requests to be processed normally
        if user_statement.strip().endswith('?') and 'vote' not in user_statement.lower():
            return None
        
        # Search for relevant documents with better query
        search_query = f"requirements specification {user_statement}"
        search_results = search_documents(search_query, n_results=5)
        
        if not search_results['documents'] or not search_results['documents'][0]:
            return None
        
        # Find the most relevant document (prefer requirements/project docs)
        best_doc = None
        best_metadata = None
        
        for i, docs in enumerate(search_results['documents']):
            if docs:
                metadata = search_results['metadatas'][i][0]
                filename = metadata.get('filename', '').lower()
                
                # Prioritize project requirements documents
                if any(keyword in filename for keyword in ['requirement', 'project', 'spec']):
                    best_doc = docs[0]
                    best_metadata = metadata
                    break
        
        # Fallback to first result if no requirements doc found
        if not best_doc:
            best_doc = search_results['documents'][0][0]
            best_metadata = search_results['metadatas'][0][0]
        
        # Use LLM to intelligently detect conflicts
        conflict_check_prompt = f"""You are an expert conflict detector. Analyze if the user's statement conflicts with the document evidence.

User Statement: "{user_statement}"

Document Evidence: "{best_doc}"

Look for conflicts such as:
- Different technology choices (React vs Vue, Python vs Java, etc.)
- Contradictory requirements or specifications
- Different budget amounts, timelines, or constraints
- Opposing methodologies or approaches
- Conflicting technical parameters or limits

A conflict exists when:
- User proposes something different from what's documented
- User suggests alternatives to documented decisions
- User states requirements that contradict the document
- User recommends approaches that differ from documented ones

Respond with JSON only:
{{"conflict": true/false, "severity": "low/medium/high", "reason": "specific explanation of the conflict"}}

Examples:
- User: "use Vue" + Doc: "use React" = conflict: true
- User: "budget $75k" + Doc: "budget $50k max" = conflict: true
- User: "6 months" + Doc: "3 months timeline" = conflict: true
"""
        
        try:
            response = await chat_completion([{"role": "user", "content": conflict_check_prompt}], temperature=0.1)
            
            # Parse JSON response
            import json
            conflict_data = json.loads(response.strip())
            
            if conflict_data.get("conflict"):
                return {
                    "user_statement": user_statement,
                    "conflicting_evidence": best_doc,
                    "source_file": best_metadata.get('filename', 'Unknown'),
                    "severity": conflict_data.get("severity", "medium"),
                    "reason": conflict_data.get("reason", "Conflict detected"),
                    "metadata": best_metadata
                }
        except Exception as e:
            print(f"Conflict detection error: {e}")
        
        return None
    
    @staticmethod
    async def _is_project_relevant(statement: str) -> bool:
        """Check if statement is project-related based on uploaded documents."""
        project_keywords = await ConflictDetector._get_dynamic_keywords()
        
        casual_keywords = [
            'hello', 'hi', 'thanks', 'thank you', 'good morning', 'good afternoon',
            'how are you', 'what\'s up', 'see you', 'bye', 'goodbye',
            'weather', 'lunch', 'coffee', 'weekend', 'vacation'
        ]
        
        statement_lower = statement.lower()
        
        # Skip if clearly casual conversation (use word boundaries to avoid false matches)
        import re
        if any(re.search(r'\b' + re.escape(casual) + r'\b', statement_lower) for casual in casual_keywords):
            return False
        
        # Check if contains project-relevant terms or is making factual claims
        has_project_terms = any(keyword in statement_lower for keyword in project_keywords)
        has_factual_claims = (
            any(char.isdigit() for char in statement) or 
            'must' in statement_lower or 'should' in statement_lower or
            'expect' in statement_lower or 'perform' in statement_lower or
            'equally' in statement_lower or 'identical' in statement_lower
        )
        
        # Also check for common technology terms
        tech_terms = ['react', 'vue', 'javascript', 'python', 'java', 'framework', 'technology', 'frontend', 'backend', 'database', 'api']
        has_tech_terms = any(tech in statement_lower for tech in tech_terms)
        
        return has_project_terms or has_factual_claims or has_tech_terms
    
    @staticmethod
    async def _get_dynamic_keywords() -> List[str]:
        """Extract keywords from uploaded documents to determine project relevance."""
        try:
            # Search for all document content to extract keywords
            search_results = search_documents("requirements project specification technology", n_results=10)
            
            if search_results['documents'] and search_results['documents'][0]:
                # Get all document content
                all_docs = []
                for docs in search_results['documents']:
                    all_docs.extend(docs)
                
                doc_content = " ".join(all_docs[:5])  # Use first 5 documents
                
                keyword_prompt = f"""Extract ALL important technical terms, technologies, frameworks, and project-specific concepts from this document content. Include:
- Technology names (React, Vue, Python, etc.)
- Framework names
- Technical terminology
- Project requirements terms
- Domain-specific concepts
- Methodology terms

Document content: {doc_content[:2000]}

Return ONLY a comma-separated list of lowercase keywords, no explanations:"""
                
                response = await chat_completion([{"role": "user", "content": keyword_prompt}], temperature=0.1)
                
                # Parse extracted keywords - handle LLM responses that include explanatory text
                if ':' in response:
                    keyword_part = response.split(':', 1)[1].strip()
                else:
                    keyword_part = response
                
                extracted_keywords = [kw.strip().lower() for kw in keyword_part.split(',') if kw.strip()]
                return extracted_keywords[:30]
        
        except Exception as e:
            print(f"Dynamic keyword extraction failed: {e}")
        
        # Fallback keywords if extraction fails
        return ['should', 'must', 'requirement', 'specification', 'technology', 'framework']

class SocraticInterventionGenerator:
    """Generates Socratic intervention messages with decision forks."""
    
    @staticmethod
    async def generate_intervention(conflict: Dict, conflict_id: str) -> str:
        """Generate intervention message with decision options."""
        
        evidence = conflict['conflicting_evidence'][:200]  # Truncate for display
        source = conflict['source_file']
        reason = conflict['reason']
        severity_emoji = {"low": "⚠️", "medium": "🚨", "high": "🛑"}
        emoji = severity_emoji.get(conflict['severity'], "⚠️")
        
        severity_text = {
            "low": "⚠️ LOW SEVERITY: Team input requested.",
            "medium": "🚨 MEDIUM SEVERITY: Team consensus recommended.", 
            "high": "🔴 HIGH SEVERITY: Team consensus required."
        }
        
        intervention = f"""✋ **CONFLICT DETECTED** {emoji}

{severity_text.get(conflict['severity'], '')} Voting period: 24 hours.

**Evidence from [{source}]:**
> "{evidence}..."

**Issue:** {reason}

**Decision Required - Choose One:**

**Option A:** Keep current strategy & document mitigation plan
**Option B:** Revise approach to align with documented evidence  
**Option C:** Challenge the evidence (provide counter-source)

Reply with: `@bot decision {conflict_id} A/B/C [your reasoning]`
"""
        return intervention

class DecisionLogger:
    """Logs team decisions for project tracking."""
    
    @staticmethod
    async def log_decision(session, conflict_id: str, selected_option: str, reasoning: str, user_id: int):
        """Log decision to database."""
        from db import Decision
        decision = Decision(
            conflict_id=conflict_id,
            triggering_conflict=conflict_id,
            selected_option=selected_option,
            reasoning=reasoning,
            decided_by=user_id
        )
        session.add(decision)
        await session.commit()
        return decision
    
    @staticmethod
    def format_decision_confirmation(option: str, reasoning: str) -> str:
        """Format decision confirmation message."""
        return f"✅ **Decision Recorded:** Team elected **Option {option}**\n\n**Reasoning:** {reasoning}"

async def get_voting_status_message(conflict_id: str, session) -> str:
    """Get current voting status for a conflict."""
    from db import ActiveConflict, ConflictVote, User
    from sqlalchemy import select, func
    from datetime import datetime
    
    conflict_res = await session.execute(
        select(ActiveConflict).where(ActiveConflict.conflict_id == conflict_id)
    )
    conflict = conflict_res.scalar_one_or_none()
    
    if not conflict:
        return "Conflict not found."
    
    votes_res = await session.execute(
        select(ConflictVote).where(ConflictVote.conflict_id == conflict_id)
    )
    votes = votes_res.scalars().all()
    
    vote_counts = {'A': 0, 'B': 0, 'C': 0}
    for vote in votes:
        vote_counts[vote.selected_option.value] += 1
    
    remaining_time = conflict.expires_at - datetime.now()
    hours_left = max(0, int(remaining_time.total_seconds() / 3600))
    
    severity_emoji = {"low": "⚠️", "medium": "🚨", "high": "🛑"}
    emoji = severity_emoji.get(conflict.severity.value, "⚠️")
    
    return f"""{emoji} **TEAM VOTING IN PROGRESS**

**Question**: {conflict.reason}
**Source**: [{conflict.source_file}]

📊 **Current Votes**: 
• A (Accept): {vote_counts['A']} votes
• B (Deny): {vote_counts['B']} votes  
• C (Modify): {vote_counts['C']} votes

⏰ **Time Remaining**: {hours_left}h

**How to Vote**:
• Chat: `@bot decision {conflict_id} A [your reasoning]`
• Sidebar: Click A/B/C buttons in Active Votes"""

async def monitor_message_for_conflicts(message_content: str, message_id: int, session) -> Optional[Dict]:
    """
    Silent observer: Check message for conflicts without responding unless conflict found.
    Returns conflict data if intervention needed.
    """
    # Only skip decision commands and very short messages
    if (message_content.startswith("@bot decision") or
        len(message_content.strip()) < 10):
        return None
    
    # Clean @bot mentions for conflict detection
    clean_content = message_content.replace("@bot", "").strip()
    
    # Check for conflicts
    conflict = await ConflictDetector.check_for_conflicts(clean_content)
    
    if conflict:
        # Store conflict in database for voting
        from datetime import datetime, timedelta
        from db import ActiveConflict, ConflictSeverity
        import uuid
        
        conflict_id = f"C{str(uuid.uuid4())[:8].upper()}"
        expires_at = datetime.now() + timedelta(hours=24)
        
        active_conflict = ActiveConflict(
            conflict_id=conflict_id,
            user_statement=conflict['user_statement'],
            conflicting_evidence=conflict['conflicting_evidence'],
            source_file=conflict['source_file'],
            severity=ConflictSeverity(conflict['severity']),
            reason=conflict['reason'],
            expires_at=expires_at
        )
        
        session.add(active_conflict)
        await session.commit()
        
        # Generate intervention with unique ID
        intervention = await SocraticInterventionGenerator.generate_intervention(conflict, conflict_id)
        
        return {
            "conflict_id": conflict_id,
            "intervention_message": intervention,
            "severity": conflict['severity']
        }
    
    return None

async def process_vote_command(message_content: str, user_id: int, session) -> Optional[str]:
    """Process @bot decision commands for voting."""
    import re
    from db import ConflictVote, ActiveConflict, DecisionOption
    from sqlalchemy import select
    
    # Parse vote command: @bot decision C1A2B3C4 A reasoning here
    match = re.match(r'@bot\s+decision\s+([A-Z0-9]+)\s+([ABC])\s+(.+)', message_content, re.IGNORECASE)
    if not match:
        return "❌ Invalid format. Use: `@bot decision CONFLICT_ID A/B/C [reasoning]`"
    
    conflict_id, option, reasoning = match.groups()
    conflict_id = conflict_id.upper()
    option = option.upper()
    
    # Check if conflict exists and is active
    conflict_res = await session.execute(
        select(ActiveConflict).where(
            ActiveConflict.conflict_id == conflict_id,
            ActiveConflict.is_resolved == False
        )
    )
    conflict = conflict_res.scalar_one_or_none()
    
    if not conflict:
        return f"❌ Conflict {conflict_id} not found or already resolved."
    
    # Check if user already voted
    existing_vote_res = await session.execute(
        select(ConflictVote).where(
            ConflictVote.conflict_id == conflict_id,
            ConflictVote.user_id == user_id
        )
    )
    existing_vote = existing_vote_res.scalar_one_or_none()
    
    if existing_vote:
        # Update existing vote
        existing_vote.selected_option = DecisionOption(option)
        existing_vote.reasoning = reasoning
    else:
        # Create new vote
        vote = ConflictVote(
            conflict_id=conflict_id,
            user_id=user_id,
            selected_option=DecisionOption(option),
            reasoning=reasoning
        )
        session.add(vote)
    
    await session.commit()
    
    # Return updated voting status
    return await get_voting_status_message(conflict_id, session)