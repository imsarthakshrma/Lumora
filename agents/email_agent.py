import asyncio
import json
import re
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from datetime import datetime
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage



class EmailProcessor:
    """
    Handles the core email processing operations (reading, parsing, categorizing)
    """
    
    def __init__(self):
        """Initialize the email processor"""
        pass
    
    async def parse_email(self, raw_email: str) -> Dict[str, Any]:
        """Parse a raw email string into structured data"""
        # Parse the email using the email module
        msg = email.message_from_string(raw_email)
        
        # Extract basic email metadata
        email_data = {
            "subject": msg.get("Subject", ""),
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "date": msg.get("Date", ""),
            "cc": msg.get("Cc", ""),
            "body": "",
            "attachments": []
        }
        
        # extract the body content
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # extract text content
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    email_data["body"] += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # track attachments
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        email_data["attachments"].append(filename)
        else:
            email_data["body"] = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return email_data
    
    async def categorize_email(self, email_data: Dict[str, Any]) -> str:
        """Categorize an email based on its content (simple rule-based approach)"""
        subject = email_data["subject"].lower()
        body = email_data["body"].lower()
        
        # simple rule-based categorization
        if any(word in subject for word in ["invoice", "payment", "bill"]):
            return "finance"
        elif any(word in subject for word in ["meeting", "schedule", "calendar"]):
            return "meeting"
        elif any(word in subject for word in ["report", "update", "status"]):
            return "report"
        elif any(word in subject for word in ["question", "help", "support"]):
            return "support"
        else:
            return "general"
    
    async def extract_action_items(self, email_data: Dict[str, Any]) -> List[str]:
        """Extract action items from an email using simple heuristics"""
        body = email_data["body"].lower()
        
        # simple pattern matching for action items
        action_patterns = [
            r"(?:please|kindly|can you|could you)[^.!?]*\?",
            r"(?:need to|must|should|have to)[^.!?]*",
            r"(?:action required|action item|to-do|todo)[^.!?]*"
        ]
        
        action_items = []
        for pattern in action_patterns:
            matches = re.findall(pattern, body)
            action_items.extend(matches)
        
        return action_items


class AsyncEmailAgent:
    """
    Async Email Agent that can read emails and generate appropriate replies
    """
    
    def __init__(self, llm=None):
        """Initialize the Email Agent with an LLM"""
        # initialize email processor
        self.email_processor = EmailProcessor()
        
        # initialize LLM if not provided
        self.llm = llm or ChatOpenAI(temperature=0)
    
    async def process_email(self, raw_email: str) -> Dict[str, Any]:
        """Process an email and extract structured information"""
        # parse the email
        email_data = await self.email_processor.parse_email(raw_email)
        
        # categorize the email
        category = await self.email_processor.categorize_email(email_data)
        email_data["category"] = category
        
        # extract action items
        action_items = await self.email_processor.extract_action_items(email_data)
        email_data["action_items"] = action_items
        
        # extract entities and relationships for knowledge graph
        kg_data = await self.extract_email_entities(email_data)
        email_data["knowledge_graph_data"] = kg_data
        
        return email_data
    
    async def extract_email_entities(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities and relationships from an email for the knowledge graph"""
        system_prompt ="""You are Dela's email analysis engine. Your role is to extract structured information from emails for workflow automation.

        Focus on identifying email-relevant entities:
        - People (sender, recipients, mentioned individuals)
        - Organizations (company names, departments)
        - Topics (main subject matter, discussion points)
        - Actions (requests, tasks, deadlines)
        - Resources (mentioned files, links, tools)

        Extract relationships that show communication patterns:
        - SENT_BY, SENT_TO, MENTIONS, REQUESTS, PROVIDES, REFERS_TO

        Always return valid JSON only, no additional text or explanations."""

        user_prompt = PromptTemplate.from_template("""Extract entities and relationships from this email for Dela's workflow automation:

        Email: {email_json}

        Return JSON in this exact format:
        {{
            "entities": [
                {{
                    "type": "entity_type",
                    "properties": {{
                        "name": "entity_name",
                        "category": "email_category",
                        "importance": "high/medium/low",
                        "automation_potential": "high/medium/low"
                    }}
                }}
            ],
            "relationships": [
                {{
                    "from_type": "entity_type1",
                    "from_props": {{"name": "entity_name1"}},
                    "rel_type": "RELATIONSHIP_TYPE",
                    "to_type": "entity_type2",
                    "to_props": {{"name": "entity_name2"}},
                    "rel_props": {{
                        "confidence": "high/medium/low",
                        "context": "relationship_context",
                        "automation_ready": "true/false"
                    }}
                }}
            ]
        }}""")

        # create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt.format()),
            HumanMessage(content=user_prompt.format(email_json=json.dumps(email_data, indent=2)))
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # extract JSON from response
        try:
            extraction = json.loads(response.content)
            return extraction
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Fallback if JSON parsing fails
            return {"entities": [], "relationships": []}
    
    async def generate_reply(self, email_data: Dict[str, Any], user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate an appropriate reply to an email"""
        system_prompt = PromptTemplate.from_template("""You are Dela's email assistant. Your role is to draft appropriate email replies based on the email content and user context.

        Follow these guidelines:
        1. Maintain a professional, friendly tone
        2. Address all questions or requests in the original email
        3. Be concise but thorough
        4. Include relevant context from the user's knowledge base
        5. Suggest next actions when appropriate
        6. Format the reply properly with greeting and signature

        Always return your response as valid JSON with the following structure:
        {
            "subject": "Reply subject line",
            "body": "Full email body with proper formatting",
            "suggested_actions": ["Action 1", "Action 2"],
            "priority": "high/medium/low",
            "follow_up_needed": true/false
        }""")

        user_prompt = """Generate an email reply for the following email:

        Original Email: {email_json}

        User Context: {user_context}

        Draft a reply that addresses all points in the original email and incorporates relevant information from the user context."""
        
        # create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt.format()),
            HumanMessage(content=user_prompt.format(
                email_json=json.dumps(email_data, indent=2),
                user_context=json.dumps(user_context or {}, indent=2)
            ))
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # extract JSON from response
        try:
            reply_data = json.loads(response.content)
            return reply_data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # fallback if JSON parsing fails
            return {
                "subject": f"Re: {email_data.get('subject', '')}",
                "body": "I'll get back to you on this soon.",
                "suggested_actions": ["Review email manually"],
                "priority": "medium",
                "follow_up_needed": True
            }
    
    async def format_email_reply(self, reply_data: Dict[str, Any], email_data: Dict[str, Any]) -> str:
        """Format the reply data into a proper email"""
        # create a new email message
        msg = MIMEMultipart()
        
        # set the email headers
        msg["Subject"] = reply_data.get("subject", f"Re: {email_data.get('subject', '')}")
        msg["From"] = email_data.get("to", "")  # The original recipient is now the sender
        msg["To"] = email_data.get("from", "")  # The original sender is now the recipient
        msg["Date"] = email.utils.formatdate()
        
        # add the email body
        body = reply_data.get("body", "")
        msg.attach(MIMEText(body, "plain"))
        
        # return the formatted email
        return msg.as_string()
    
    async def learn_from_emails(self, emails: List[str]) -> List[Dict[str, Any]]:
        """Learn from a batch of emails"""
        results = []
        # process emails concurrently for better performance
        email_tasks = [self.process_email(email) for email in emails]
        results = await asyncio.gather(*email_tasks)
        return results


# # Example usage
# async def main():
#     # Create an email agent
#     email_agent = AsyncEmailAgent()
    
#     # Example raw email
#     raw_email = """From: john.doe@example.com
# To: jane.smith@company.com
# Subject: Weekly Sales Report - Q2 2025
# Date: Mon, 14 Jul 2025 09:30:00 -0700

# Hi Jane,

# Attached is the weekly sales report for Q2 2025. Here are the key highlights:

# 1. Total sales: $1.2M (15% increase from last quarter)
# 2. New customers: 45
# 3. Top performing product: Product X (35% of total sales)

# Could you please review and share your thoughts by Wednesday? Also, I'd like to schedule a meeting to discuss the marketing strategy for Q3.

# Thanks,
# John
# """
    
#     # Process the email
#     email_data = await email_agent.process_email(raw_email)
    
#     # Generate a reply
#     user_context = {
#         "name": "Jane Smith",
#         "role": "Marketing Director",
#         "preferences": {
#             "meeting_times": ["Tuesday afternoon", "Thursday morning"],
#             "report_format": "Executive summary with visual data"
#         },
#         "recent_activities": [
#             "Reviewed Q1 marketing performance",
#             "Preparing Q3 marketing strategy"
#         ]
#     }
    
#     reply = await email_agent.generate_reply(email_data, user_context)
    
#     # Format the reply as an email
#     formatted_reply = await email_agent.format_email_reply(reply, email_data)
    
#     print("Processed Email Data:")
#     print(json.dumps(email_data, indent=2))
#     print("\nGenerated Reply:")
#     print(json.dumps(reply, indent=2))
#     print("\nFormatted Email Reply:")
#     print(formatted_reply)


# if __name__ == "__main__":
#     asyncio.run(main())