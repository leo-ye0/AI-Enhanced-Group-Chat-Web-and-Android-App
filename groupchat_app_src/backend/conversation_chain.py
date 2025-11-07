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
        # Search for relevant documents
        search_results = search_documents(user_question, n_results=3)
        
        # Build context from vector database
        context = ""
        if search_results['documents'] and search_results['documents'][0]:
            context = "\n\nRelevant information from uploaded documents:\n"
            for doc in search_results['documents'][0]:
                context += f"- {doc[:300]}...\n"
        
        # Build conversation messages
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are a helpful assistant in a group chat. Use the conversation history "
                    "and provided document context to give accurate, concise responses. "
                    "Reference previous messages when relevant."
                    f"{context}"
                )
            }
        ]
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current question
        messages.append({"role": "user", "content": user_question})
        
        # Generate response
        response = await chat_completion(messages)
        
        # Update conversation history
        self.add_to_history("user", user_question)
        self.add_to_history("assistant", response)
        
        return response

# Global conversation chain instance
conversation_chain = ConversationChain(max_history=50)