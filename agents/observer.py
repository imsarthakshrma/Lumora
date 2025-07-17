import json
import asyncio
from typing import Dict, Any
from datetime import datetime
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

class Observer:
    """
    Observer agent that monitors patterns, updates the knowledge graph, and learns from interactions.
    This agent is responsible for identifying patterns in user behavior and email interactions,
    updating the knowledge graph with new information, and learning from these interactions.
    """
    
    def __init__(self, kg_agent, llm=None):
        """
        Initialize the Observer agent.
        
        Args:
            kg_agent: Knowledge Graph Agent instance
            llm: LangChain language model instance (optional)
        """
        self.kg_agent = kg_agent
        self.llm = llm or ChatOpenAI(
            temperature=0.1,
            model="gpt-4o",
        )
        self.interaction_history = []
        
    async def observe_email_interaction(self, email_data: Dict[str, Any], response_data: Dict[str, Any] = None):
        """
        Observe an email interaction and update the knowledge graph.
        
        Args:
            email_data: Dictionary containing email data and analysis
            response_data: Dictionary containing response data (if any)
        """
        # Record interaction in history
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "email_data": email_data,
            "response_data": response_data,
        }
        self.interaction_history.append(interaction)
        
        # Extract entities and relationships for knowledge graph
        if "kg_data" not in email_data:
            # If kg_data is not already in email_data, we need to extract it
            # This would typically be done by the Analyser, but we handle it here as a fallback
            kg_data = await self._extract_kg_data(email_data)
        else:
            kg_data = email_data["kg_data"]
        
        # Update knowledge graph with extracted data
        await self.kg_agent.process_task({"email_interaction": email_data, "kg_data": kg_data})
        
        # Learn from interaction
        await self._learn_from_interaction(interaction)
        
    async def _extract_kg_data(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract knowledge graph data from email data.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            Dictionary containing entities and relationships
        """
        system_prompt = """You are Dela's knowledge graph extraction engine. Your role is to analyze email data and extract structured information for workflow automation.

Focus on identifying workflow-relevant entities:
- People (sender, recipients, mentioned individuals)
- Organizations (companies, departments)
- Documents (invoices, reports, attachments)
- Systems (software, platforms mentioned)
- Tasks (action items, requests)

Extract relationships that show workflow dependencies:
- SENT_BY (email SENT_BY person)
- RECEIVED_BY (email RECEIVED_BY person)
- MENTIONS (email MENTIONS person/org/system)
- CONTAINS (email CONTAINS document/task)
- REQUESTS (email REQUESTS action/information)
- RELATED_TO (email RELATED_TO previous communication)

Always return valid JSON only, no additional text or explanations."""

        user_prompt = f"""Extract entities and relationships from this email data for Dela's knowledge graph:

Email Data: {json.dumps(email_data, indent=2)}

Return a JSON object with the following structure:
{{
    "entities": [
        {{
            "type": "string",
            "properties": {{
                "name": "string",
                "id": "string",
                "other_properties": "as needed"
            }}
        }}
    ],
    "relationships": [
        {{
            "from_type": "string",
            "from_properties": {{
                "identifying_property": "value"
            }},
            "to_type": "string",
            "to_properties": {{
                "identifying_property": "value"
            }},
            "type": "string",
            "properties": {{
                "optional_properties": "as needed"
            }}
        }}
    ]
}}"""

        # create messages for the LLM   
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt.format(email_json=json.dumps(email_data, indent=2)))
        ]
        
        # Get response from LLM
        response = asyncio.run(self.llm.invoke(messages))
        
        try:
            # Extract and parse JSON from response
            content = response.content
            if isinstance(content, str):
                import re
                # Find JSON content (in case there's additional text)
                json_match = re.search(r'({.*})', content.replace('\n', ' '), re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                kg_data = json.loads(content)
            else:
                kg_data = {"entities": [], "relationships": []}
                
            return kg_data
        except Exception as e:
            print(f"Error parsing KG extraction result: {e}")
            return {"entities": [], "relationships": []}
    
    async def _learn_from_interaction(self, interaction: Dict[str, Any]):
        """
        Learn from an interaction and update the knowledge graph with patterns.
        
        Args:
            interaction: Dictionary containing interaction data
        """
        # Skip if we don't have enough history
        if len(self.interaction_history) < 2:
            return
        
        # Analyze patterns in recent interactions
        system_prompt = """You are Dela's pattern recognition engine. Your role is to analyze email interactions and identify patterns in user behavior.

Focus on identifying:
- Common email categories and how they're handled
- Recurring entities (people, organizations) and their relationships
- Time patterns in communications
- Response patterns based on email content
- Automation opportunities based on repetitive tasks

Always return valid JSON only, no additional text or explanations."""

        # Get the last 5 interactions or all if less than 5
        recent_interactions = self.interaction_history[-5:]
        
        user_prompt = f"""Analyze these recent email interactions and identify patterns:

Recent Interactions: {json.dumps(recent_interactions, indent=2)}

Return a JSON object with the following structure:
{{
    "identified_patterns": [
        {{
            "pattern_type": "string",
            "description": "string",
            "confidence": "float (0-1)",
            "supporting_evidence": "string"
        }}
    ],
    "automation_opportunities": [
        {{
            "description": "string",
            "trigger_condition": "string",
            "suggested_action": "string",
            "confidence": "float (0-1)"
        }}
    ],
    "entity_insights": [
        {{
            "entity_type": "string",
            "entity_name": "string",
            "insight": "string"
        }}
    ]
}}"""

        # Create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt.format(email_json=json.dumps(recent_interactions, indent=2)))
        ]
        
        # Get response from LLM
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract and parse JSON from response
            content = response.content
            if isinstance(content, str):
                import re
                # Find JSON content (in case there's additional text)
                json_match = re.search(r'({.*})', content.replace('\n', ' '), re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                pattern_data = json.loads(content)
                
                # Create a task for the knowledge graph agent to process
                task = {
                    "pattern_analysis": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Update knowledge graph with pattern data
                await self.kg_agent.process_task(task)
            
        except Exception as e:
            print(f"Error processing pattern analysis: {e}")
    
    async def get_user_preferences(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get user preferences based on context and knowledge graph.
        
        Args:
            context: Dictionary containing context information
            
        Returns:
            Dictionary containing user preferences
        """
        # Query the knowledge graph for user preferences
        try:
            # Construct a question for the knowledge graph
            question = f"What are the user's preferences for handling {context.get('category', 'general')} emails?"
            
            # Get answer from knowledge graph
            result = await self.kg_agent.answer_question(question)
            
            return result
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return {}