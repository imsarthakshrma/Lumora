import json
import re
from typing import Dict, Any
# import asyncio
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from email.message import Message

class Analyser:
    """
    Analyser agent that processes emails, extracts key information, and determines intent.
    This agent is responsible for understanding the content of emails and extracting
    structured information for further processing.
    """
    
    def __init__(self, llm=None):
        """
        Initialize the Analyser agent.
        
        Args:
            llm: LangChain language model instance (optional)
        """
        self.llm = llm or ChatOpenAI(
            temperature=0.1,
            model="gpt-4o",
        )
    
    async def analyse_email(self, email_message: Message) -> Dict[str, Any]:
        """
        Analyse an email message to extract key information and determine intent.
        
        Args:
            email_message: Email message to analyse
            
        Returns:
            Dictionary containing extracted information and intent
        """
        # Extract basic email metadata
        email_data = self._extract_email_metadata(email_message)
        
        # Extract email content
        email_content = self._extract_email_content(email_message)
        email_data["content"] = email_content
        
        # Analyse email content using LLM
        analysis_result = await self._analyse_content(email_data)
        
        # Merge results
        email_data.update(analysis_result)
        
        return email_data
    
    def _extract_email_metadata(self, email_message: Message) -> Dict[str, Any]:
        """
        Extract basic metadata from an email message.
        
        Args:
            email_message: Email message
            
        Returns:
            Dictionary containing email metadata
        """
        metadata = {
            "subject": email_message.get("Subject", ""),
            "from": email_message.get("From", ""),
            "to": email_message.get("To", ""),
            "date": email_message.get("Date", ""),
            "message_id": email_message.get("Message-ID", ""),
        }
        
        return metadata
    
    def _extract_email_content(self, email_message: Message) -> str:
        """
        Extract content from an email message.
        
        Args:
            email_message: Email message
            
        Returns:
            Extracted email content as text
        """
        content = ""
        
        # Handle multipart messages
        if email_message.is_multipart():
            for part in email_message.get_payload():
                if part.get_content_type() == "text/plain":
                    content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    break
        else:
            # Handle single part messages
            if email_message.get_content_type() == "text/plain":
                content = email_message.get_payload(decode=True).decode(email_message.get_content_charset() or 'utf-8', errors='replace')
        
        # Clean up content
        content = re.sub(r'\r\n', '\n', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    async def _analyse_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse email content using LLM to extract intent and key information.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            Dictionary containing analysis results
        """
        system_prompt = """You are Dela's email analysis engine. Your role is to analyze emails and extract structured information.

Focus on identifying:
- Primary intent of the email (request, information, follow-up, etc.)
- Key entities mentioned (people, organizations, products, etc.)
- Any action items or requests
- Priority level (high, medium, low)
- Category (invoice, meeting, task, etc.)
- Sentiment (positive, negative, neutral)

If the email contains an invoice or payment request, extract:
- Invoice number
- Amount
- Due date
- Vendor/supplier name
- Payment method requested (if any)

Always return valid JSON only, no additional text or explanations."""

        user_prompt = f"""Analyze this email and extract structured information:

From: {email_data['from']}
To: {email_data['to']}
Subject: {email_data['subject']}
Date: {email_data['date']}

Content:
{email_data['content']}

Return a JSON object with the following structure:
{{
    "intent": "string",
    "category": "string",
    "priority": "string",
    "sentiment": "string",
    "entities": [
        {{
            "type": "string",
            "name": "string",
            "relevance": "string"
        }}
    ],
    "action_items": [
        {{
            "description": "string",
            "due_date": "string or null",
            "assignee": "string or null"
        }}
    ],
    "invoice_data": {{
        "is_invoice": true/false,
        "invoice_number": "string or null",
        "amount": "string or null",
        "currency": "string or null",
        "due_date": "string or null",
        "vendor": "string or null",
        "payment_method": "string or null"
    }},
    "summary": "string"
}}"""

        # create messages for the LLM   
        messages = [
            SystemMessage(content=system_prompt.format()),
            HumanMessage(content=user_prompt.format(email_json=json.dumps(email_data, indent=2)))
        ]
        
        # get response from LLM
        response = await self.llm.ainvoke(messages)
        
        try:
            # extract and parse JSON from response
            content = response.content
            # handle potential formatting issues in the response
            if isinstance(content, str):
                # find JSON content (in case there's additional text)
                json_match = re.search(r'({.*})', content.replace('\n', ' '), re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                analysis_result = json.loads(content)
            else:
                analysis_result = {}
                
            return analysis_result
        except Exception as e:
            print(f"Error parsing analysis result: {e}")
            return {
                "intent": "unknown",
                "category": "unknown",
                "priority": "medium",
                "sentiment": "neutral",
                "entities": [],
                "action_items": [],
                "invoice_data": {"is_invoice": False},
                "summary": "Failed to analyze email content"
            }
    
    async def detect_invoice(self, email_data: Dict[str, Any]) -> bool:
        """
        Detect if an email contains an invoice based on analysis results.
        
        Args:
            email_data: Dictionary containing email data and analysis
            
        Returns:
            True if the email contains an invoice, False otherwise
        """
        # check if invoice_data exists and is_invoice is True
        if "invoice_data" in email_data and email_data["invoice_data"].get("is_invoice", False):
            return True
            
        # check if category is invoice
        if email_data.get("category", "").lower() == "invoice":
            return True
            
        # check subject and content for invoice-related keywords
        invoice_keywords = ["invoice", "payment", "bill", "receipt", "due", "statement", "charge"]
        subject = email_data.get("subject", "").lower()
        content = email_data.get("content", "").lower()
        
        for keyword in invoice_keywords:
            if keyword in subject or keyword in content:
                return True
                
        return False
    
    async def extract_entities_for_kg(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities and relationships for the knowledge graph.
        
        Args:
            email_data: Dictionary containing email data and analysis
            
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
            SystemMessage(content=system_prompt.format()),
            HumanMessage(content=user_prompt.format(email_json=json.dumps(email_data, indent=2)))
        ]
        
        # get response from LLM
        response = await self.llm.ainvoke(messages)
        
        try:
            # extract and parse JSON from response
            content = response.content
            # handle potential formatting issues in the response
            if isinstance(content, str):
                # find JSON content (in case there's additional text)
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