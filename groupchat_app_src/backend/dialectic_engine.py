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
    async def check_for_conflicts(user_statement: str, session=None) -> Optional[Dict]:
        """Check if user statement conflicts with uploaded documents."""
        print(f"\n🔍 DIALECTIC ENGINE: Monitoring '{user_statement[:60]}...'")
        
        # Skip task/role assignments - these are operational, not strategic
        task_keywords = ['assign', 'assigned', 'task for', 'give this to', 'can you do', 'responsible for']
        if any(keyword in user_statement.lower() for keyword in task_keywords):
            print("  ⏭️  Skipped: Task assignment (operational, not strategic)")
            return None
        
        # Skip pure questions (not proposals)
        if user_statement.strip().endswith('?'):
            rhetorical_indicators = ['i think', 'we should', 'let\'s', 'propose', 'suggest']
            is_rhetorical = any(indicator in user_statement.lower() for indicator in rhetorical_indicators)
            if not is_rhetorical:
                print("  ⏭️  Skipped: Question (not a declarative statement)")
                return None
        
        # Search past decisions first
        past_decision = None
        if session:
            past_decision = await ConflictDetector._check_past_decisions(user_statement, session)
            if past_decision:
                print(f"  📋 Found past decision: {past_decision['decision_summary']}")
                return past_decision
        
        # Search for relevant documents with better query
        search_query = f"requirements specification {user_statement}"
        print(f"  🔎 Searching for conflicts...")
        search_results = search_documents(search_query, n_results=5)
        
        if not search_results['documents'] or not search_results['documents'][0]:
            print("  ✅ No conflicts found (no relevant docs)")
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
        
        # Use LLM to intelligently detect conflicts with enhanced context
        conflict_check_prompt = f"""You are a JSON-only conflict detector. Respond ONLY with valid JSON, no code, no explanations.

User statement: "{user_statement}"
Document: "{best_doc}"

Conflict = user proposes different tech/time/amount/approach than document.

Examples:
- "use Streamlit" vs "use React" = conflict
- "use Vue" vs "use React" = conflict  
- "meeting 3pm" vs "meeting 2pm" = conflict
- "budget $50k" vs "budget $30k" = conflict
- "use React hooks" vs "use React" = no conflict

Classify conflict type: technical, timeline, budget, methodology, or scope.
Assess confidence: 0-100 (how certain this is a real conflict).

Respond with ONLY this JSON (no markdown, no code blocks):
{{"conflict": true, "severity": "high", "reason": "Streamlit vs React", "category": "technical", "confidence": 95}}

Your JSON:"""
        
        try:
            response = await chat_completion([{"role": "user", "content": conflict_check_prompt}], temperature=0.0)
            
            # Parse JSON response - extract JSON if wrapped in markdown
            import json
            import re
            
            # Remove markdown code blocks if present
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response.strip()
            
            conflict_data = json.loads(json_str)
            
            print(f"  🤖 LLM: {conflict_data}")
            if conflict_data.get("conflict"):
                confidence = conflict_data.get("confidence", 50)
                # Skip low-confidence conflicts (< 70%)
                if confidence < 70:
                    print(f"  ⚠️  Low confidence ({confidence}%), skipping")
                    return None
                
                print(f"  🚨 CONFLICT DETECTED!")
                print(f"     Severity: {conflict_data.get('severity', 'medium').upper()}")
                print(f"     Category: {conflict_data.get('category', 'general').upper()}")
                print(f"     Confidence: {confidence}%")
                print(f"     Source: {best_metadata.get('filename', 'Unknown')}")
                print(f"     Reason: {conflict_data.get('reason', 'Conflict detected')}")
                return {
                    "user_statement": user_statement,
                    "conflicting_evidence": best_doc,
                    "source_file": best_metadata.get('filename', 'Unknown'),
                    "severity": conflict_data.get("severity", "medium"),
                    "reason": conflict_data.get("reason", "Conflict detected"),
                    "category": conflict_data.get("category", "general"),
                    "confidence": confidence,
                    "metadata": best_metadata
                }
            else:
                print(f"  ✅ No conflict (Doc: {best_doc[:80]}...)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print(f"     LLM response: {response if 'response' in locals() else 'N/A'}")
        
        return None
    
    @staticmethod
    async def _is_project_relevant(statement: str) -> bool:
        """Check if statement is project-related using smart LLM analysis."""
        casual_keywords = [
            'hello', 'hi', 'thanks', 'thank you', 'good morning', 'good afternoon',
            'how are you', 'what\'s up', 'see you', 'bye', 'goodbye',
            'weather', 'lunch', 'coffee', 'weekend', 'vacation'
        ]
        
        statement_lower = statement.lower()
        
        # Skip if clearly casual conversation
        import re
        if any(re.search(r'\b' + re.escape(casual) + r'\b', statement_lower) for casual in casual_keywords):
            return False
        
        # Skip very short messages
        if len(statement.strip()) < 15:
            return False
        
        # Use LLM to determine if statement is making a technical/project claim
        relevance_prompt = f"""Is this statement making a technical, project-related, or decision-oriented claim?

Statement: "{statement}"

A statement is project-relevant if it:
- Proposes a technology, tool, or approach
- Makes claims about requirements, timelines, or budgets
- Suggests methodologies or processes
- States technical specifications or constraints

Respond with only: YES or NO"""
        
        try:
            response = await chat_completion([{"role": "user", "content": relevance_prompt}], temperature=0.1)
            return "yes" in response.lower()
        except:
            # Fallback to simple keyword check
            return 'should' in statement_lower or 'must' in statement_lower or any(char.isdigit() for char in statement)
    
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
    
    @staticmethod
    async def _check_past_decisions(user_statement: str, session) -> Optional[Dict]:
        """Check if user statement relates to a previously resolved conflict."""
        from db import Decision, User
        from sqlalchemy import select, desc
        
        # Get recent decisions (last 50)
        result = await session.execute(
            select(Decision, User.username)
            .join(User, Decision.decided_by == User.id)
            .order_by(desc(Decision.created_at))
            .limit(50)
        )
        decisions = result.all()
        
        if not decisions:
            return None
        
        # Build decision context for LLM
        decision_context = "\n".join([
            f"- {d.Decision.created_at.strftime('%Y-%m-%d')}: Option {d.Decision.selected_option.value} - {d.Decision.reasoning[:100]}"
            for d in decisions[:10]
        ])
        
        # Check if statement conflicts with past decision
        check_prompt = f"""Does this user statement contradict or revisit a previously resolved decision?

User statement: "{user_statement}"

Past decisions:
{decision_context}

If the statement proposes something already decided, respond with JSON:
{{"revisits_decision": true, "decision_date": "YYYY-MM-DD", "original_choice": "A/B/C", "summary": "brief summary"}}

If no conflict with past decisions, respond:
{{"revisits_decision": false}}

Your JSON:"""
        
        try:
            response = await chat_completion([{"role": "user", "content": check_prompt}], temperature=0.0)
            import json, re
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                if result.get("revisits_decision"):
                    return {
                        "is_past_decision_reference": True,
                        "decision_date": result.get("decision_date"),
                        "original_choice": result.get("original_choice"),
                        "decision_summary": result.get("summary", "Previous decision found")
                    }
        except Exception as e:
            print(f"  ⚠️  Past decision check failed: {e}")
        
        return None

class SocraticInterventionGenerator:
    """Generates Socratic intervention messages with decision forks."""
    
    @staticmethod
    async def generate_intervention(conflict: Dict, conflict_id: str) -> str:
        """Generate intervention message with decision options."""
        
        # Check if this is a past decision reference
        if conflict.get('is_past_decision_reference'):
            return f"""📋 **PAST DECISION REFERENCE**

ℹ️ This topic was previously resolved on **{conflict['decision_date']}**.

**Original Decision:** Team chose **Option {conflict['original_choice']}**
**Summary:** {conflict['decision_summary']}

💡 If you want to revisit this decision, please provide new evidence or changed circumstances."""
        
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
        
        category = conflict.get('category', 'general').upper()
        confidence = conflict.get('confidence', 50)
        
        intervention = f"""✋ **CONFLICT DETECTED** {emoji}

{severity_text.get(conflict['severity'], '')} Voting period: 2 hours.
**Category:** {category} | **Confidence:** {confidence}%

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

async def monitor_message_for_conflicts(message_content: str, message_id: int, session, group_id: int = None) -> Optional[Dict]:
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
    
    # Check for conflicts (pass session for decision history lookup)
    conflict = await ConflictDetector.check_for_conflicts(clean_content, session)
    
    if conflict:
        # If this is a past decision reference, don't create new conflict
        if conflict.get('is_past_decision_reference'):
            intervention = await SocraticInterventionGenerator.generate_intervention(conflict, None)
            return {
                "conflict_id": None,
                "intervention_message": intervention,
                "severity": "info",
                "is_reference": True
            }
        
        # Store conflict in database for voting
        from datetime import datetime, timedelta
        from db import ActiveConflict, ConflictSeverity
        import uuid
        
        conflict_id = f"C{str(uuid.uuid4())[:8].upper()}"
        expires_at = datetime.now() + timedelta(hours=2)
        
        active_conflict = ActiveConflict(
            conflict_id=conflict_id,
            user_statement=conflict['user_statement'],
            conflicting_evidence=conflict['conflicting_evidence'],
            source_file=conflict['source_file'],
            severity=ConflictSeverity(conflict['severity']),
            reason=conflict['reason'],
            expires_at=expires_at,
            group_id=group_id
        )
        
        session.add(active_conflict)
        await session.commit()
        
        # Generate intervention with unique ID
        intervention = await SocraticInterventionGenerator.generate_intervention(conflict, conflict_id)
        
        print(f"\n📢 INTERVENTION SENT: Conflict ID {conflict_id}")
        print(f"   Team must vote: A/B/C within 24 hours")
        
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