from typing import List, Dict
from vector_db import search_documents
from llm import chat_completion

class ConversationChain:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({"role": role, "content": content})
        # Keep only recent messages
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    async def get_response(self, user_question: str) -> str:
        """Generate response using conversation history and vector search"""
        print(f"\n🤖 Processing: '{user_question}'")
        # Multi-strategy search for better precision
        search_results = search_documents(user_question, n_results=8)
        
        # If initial search fails, try key terms from the question
        if not search_results['documents'] or not search_results['documents'][0]:
            key_terms = [word for word in user_question.lower().replace('?', '').split() if len(word) > 2]
            for term in key_terms:
                alt_search = search_documents(term, n_results=5)
                if alt_search['documents'] and alt_search['documents'][0]:
                    search_results = alt_search
                    print(f"Alternative search with '{term}' found results")
                    break
        
        # Build context with relevance filtering
        context = ""
        if search_results['documents'] and search_results['documents'][0]:
            context = "\n\nRelevant information from uploaded documents:\n"
            # Filter and rank by relevance if distances are available
            docs_with_scores = list(zip(search_results['documents'][0], 
                                      search_results.get('distances', [[]])[0] or [0]*len(search_results['documents'][0])))
            # Sort by distance (lower is better) and take top 5
            docs_with_scores.sort(key=lambda x: x[1])
            print(f"📝 Injecting {len(docs_with_scores[:5])} chunks into LLM context")
            for doc, score in docs_with_scores[:5]:
                context += f"- {doc[:600]}...\n\n"
        else:
            print("⚠️  No relevant documents found - using general knowledge")
        
        # Build conversation messages with current date context
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        messages = [
            {
                "role": "system", 
                "content": (
                    f"You are a helpful assistant in a group chat. Today's date is {current_date}. "
                    "When providing timelines or project phases, always use realistic dates starting from the current date. "
                    "Prioritize information from uploaded documents and conversation history, "
                    "but you can use your general knowledge to answer questions when documents don't contain the information. "
                    "Always clearly indicate when you're using general knowledge vs. document information. "
                    "CRITICAL: Never make up or hallucinate tasks, assignments, or project-specific information that isn't in the context."
                    f"{context}"
                )
            }
        ]
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current question
        messages.append({"role": "user", "content": user_question})
        
        # Use LLM to detect various request types naturally
        intent_prompt = f"""Analyze this user message and determine what type of request it is. Respond with only one of these options:

VOTE - if asking to start/create a team vote or poll
MILESTONE - if asking for help creating/generating project milestones, phases, stages, or timeline
TASK - if asking to create/add tasks or assignments
MEETING - if asking to schedule/create a meeting
STATUS - if asking about project status or progress
NORMAL - for regular questions or conversation

User message: "{user_question}"

Examples:
- "let's vote on this" -> VOTE
- "should we decide this together?" -> VOTE
- "help me plan the project phases" -> MILESTONE
- "what stages do we need?" -> MILESTONE
- "add a task to review code" -> TASK
- "we need to do X by Friday" -> TASK
- "let's meet tomorrow" -> MEETING
- "schedule a call" -> MEETING
- "how are we doing?" -> STATUS
- "what's our progress?" -> STATUS
- "explain this concept" -> NORMAL"""
        
        try:
            intent_response = await chat_completion([{"role": "user", "content": intent_prompt}], temperature=0.1)
            intent = intent_response.strip().upper()
            
            if intent == "VOTE":
                # Extract vote question naturally
                vote_prompt = f"""Extract the main question or topic for voting from this message. Make it a clear yes/no question.

User message: "{user_question}"

Return only the question, nothing else."""
                try:
                    vote_question = await chat_completion([{"role": "user", "content": vote_prompt}], temperature=0.1)
                    return f"__VOTE_REQUEST__{vote_question.strip()}"
                except:
                    return f"__VOTE_REQUEST__Should we proceed with this decision?"
            
            elif intent == "MILESTONE":
                return "__MILESTONE_REQUEST__"
            
            elif intent == "TASK":
                return "__TASK_REQUEST__"
            
            elif intent == "MEETING":
                return "__MEETING_REQUEST__"
            
            elif intent == "STATUS":
                return "__STATUS_REQUEST__"
                
        except:
            pass
        
        # Generate response
        print("🗨️  Calling LLM...")
        response = await chat_completion(messages)
        print(f"✅ Response generated: {response[:100]}...\n")
        
        # Update conversation history
        self.add_to_history("user", user_question)
        self.add_to_history("assistant", response)
        
        return response

# Global conversation chain instance
conversation_chain = ConversationChain(max_history=50)

def clear_conversation_history():
    """Clear the conversation history"""
    global conversation_chain
    conversation_chain.conversation_history = []