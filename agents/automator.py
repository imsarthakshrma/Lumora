import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

class Automator:
    """
    Automator agent that takes actions based on analysis and knowledge.
    This agent is responsible for generating email replies, scheduling actions,
    and automating repetitive tasks based on user preferences and knowledge graph.
    """
    
    def __init__(self, observer, llm=None):
        """
        Initialize the Automator agent.
        
        Args:
            observer: Observer agent instance
            llm: LangChain language model instance (optional)
        """
        self.observer = observer
        self.llm = llm or ChatOpenAI(
            temperature=0.2,
            model="gpt-4o",
        )
    
    async def generate_email_reply(self, email_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an email reply based on email data, user preferences, and knowledge graph.
        
        Args:
            email_data: Dictionary containing email data and analysis
            user_profile: Dictionary containing user profile data
            
        Returns:
            Dictionary containing generated reply
        """
        # Get user preferences for this type of email
        user_preferences = await self.observer.get_user_preferences({
            "category": email_data.get("category", "general"),
            "from": email_data.get("from", ""),
            "subject": email_data.get("subject", "")
        })
        
        # Generate reply using LLM
        system_prompt = """You are Dela's email reply generator. Your role is to generate appropriate email replies based on the original email, user profile, and user preferences.

Your replies should:
- Match the user's communication style and tone
- Address all questions or requests in the original email
- Be concise and professional
- Follow any specific preferences or rules from the user profile
- Include appropriate greetings and sign-offs

Always return valid JSON only with the following structure:
{
    "subject": "Reply subject line",
    "body": "Full email body with greeting and sign-off",
    "summary": "Brief summary of the reply"
}"""

        user_prompt = f"""Generate an email reply based on the following:

Original Email:
From: {email_data.get('from', '')}
To: {email_data.get('to', '')}
Subject: {email_data.get('subject', '')}
Content: {email_data.get('content', '')}

Email Analysis:
{json.dumps(email_data, indent=2)}

User Profile:
{json.dumps(user_profile, indent=2)}

User Preferences:
{json.dumps(user_preferences, indent=2)}

Generate a reply that matches the user's style and addresses all points in the original email."""

        # Create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
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
                
                try:
                    reply_data = self._extract_json_from_llm_response(response.content)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error extracting JSON from LLM response: {e}", exc_info=True)
                    reply_data = {
                        "subject": f"Re: {email_data.get('subject', '')}",
                        "body": "I'll get back to you soon.",
                        "summary": "Generic reply"
                    }
            else:
                reply_data = {
                    "subject": f"Re: {email_data.get('subject', '')}",
                    "body": "I'll get back to you soon.",
                    "summary": "Generic reply"
                }
                
            # Format as email message
            reply_message = self._format_email_reply(
                to=email_data.get("from", ""),
                from_addr=email_data.get("to", ""),
                subject=reply_data.get("subject", f"Re: {email_data.get('subject', '')}"),
                body=reply_data.get("body", "")
            )
            
            # Add reply message to reply_data
            reply_data["message"] = reply_message
            
            # Notify observer about this interaction
            await self.observer.observe_email_interaction(email_data, reply_data)
            
            return reply_data
            
        except Exception as e:
            logger.error(f"Error generating email reply: {e}", exc_info=True)
            return {
                "subject": f"Re: {email_data.get('subject', '')}",
                "body": "I'll get back to you soon.",
                "summary": "Error generating reply",
                "error": "An error occurred while generating the reply."
            }
    
    def _format_email_reply(self, to: str, from_addr: str, subject: str, body: str) -> MIMEMultipart:
        """
        Format an email reply as a MIME message.
        
        Args:
            to: Recipient email address
            from_addr: Sender email address
            subject: Email subject
            body: Email body
            
        Returns:
            Formatted email message
        """
        # Create message
        message = MIMEMultipart()
        message["To"] = to
        message["From"] = from_addr
        message["Subject"] = subject
        
        # Attach body
        message.attach(MIMEText(body, "plain"))
        
        return message
    
    async def process_invoice(self, email_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an invoice from an email based on user preferences.
        
        Args:
            email_data: Dictionary containing email data and analysis
            user_profile: Dictionary containing user profile data
            
        Returns:
            Dictionary containing processing results
        """
        # Extract invoice data
        invoice_data = email_data.get("invoice_data", {})
        
        if not invoice_data.get("is_invoice", False):
            return {
                "success": False,
                "message": "No invoice detected in email"
            }
        
        # Get user preferences for invoice processing
        user_preferences = await self.observer.get_user_preferences({
            "category": "invoice",
            "vendor": invoice_data.get("vendor", "")
        })
        
        # Validate invoice against user preferences
        validation_result = await self._validate_invoice(invoice_data, user_preferences)
        
        if not validation_result["valid"]:
            # Generate rejection reply
            rejection_reply = await self.generate_invoice_rejection(
                email_data, 
                invoice_data, 
                validation_result["reasons"],
                user_profile
            )
            
            return {
                "success": False,
                "message": "Invoice validation failed",
                "validation_result": validation_result,
                "rejection_reply": rejection_reply
            }
        
        # Generate approval reply
        approval_reply = await self.generate_invoice_approval(
            email_data,
            invoice_data,
            user_profile
        )
        
        return {
            "success": True,
            "message": "Invoice processed successfully",
            "validation_result": validation_result,
            "approval_reply": approval_reply
        }
    
    async def _validate_invoice(self, invoice_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an invoice against user preferences.
        
        Args:
            invoice_data: Dictionary containing invoice data
            user_preferences: Dictionary containing user preferences
            
        Returns:
            Dictionary containing validation results
        """
        system_prompt = """You are Dela's invoice validation engine. Your role is to validate invoices against user preferences.

Check for:
- Amount limits (is the invoice amount within acceptable limits?)
- Approved vendors (is the vendor on the approved list?)
- Payment terms (are the payment terms acceptable?)
- Due date (is there enough time to process the payment?)
- Required information (does the invoice have all required fields?)

Always return valid JSON only with the following structure:
{
    "valid": true/false,
    "reasons": ["reason1", "reason2", ...],
    "confidence": float (0-1)
}"""

        user_prompt = f"""Validate this invoice against user preferences:

Invoice Data:
{json.dumps(invoice_data, indent=2)}

User Preferences:
{json.dumps(user_preferences, indent=2)}

Return a JSON object indicating whether the invoice is valid and any reasons for rejection."""

        # Create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
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
                
                validation_result = json.loads(content)
            else:
                validation_result = {
                    "valid": False,
                    "reasons": ["Unable to validate invoice"],
                    "confidence": 0.0
                }
                
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating invoice: {e}", exc_info=True)
            return {
                "valid": False,
                "reasons": ["An error occurred while validating the invoice"],
                "confidence": 0.0
            }
    
    async def generate_invoice_approval(self, email_data: Dict[str, Any], invoice_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an invoice approval reply.
        
        Args:
            email_data: Dictionary containing email data
            invoice_data: Dictionary containing invoice data
            user_profile: Dictionary containing user profile data
            
        Returns:
            Dictionary containing approval reply
        """
        system_prompt = """You are Dela's invoice approval reply generator. Your role is to generate appropriate approval replies for invoices.

Your replies should:
- Confirm receipt of the invoice
- Confirm that the invoice has been approved for payment
- Provide any relevant payment information
- Be professional and concise
- Match the user's communication style

Always return valid JSON only with the following structure:
{
    "subject": "Reply subject line",
    "body": "Full email body with greeting and sign-off",
    "summary": "Brief summary of the reply"
}"""

        user_prompt = f"""Generate an invoice approval reply based on the following:

Original Email:
From: {email_data.get('from', '')}
To: {email_data.get('to', '')}
Subject: {email_data.get('subject', '')}

Invoice Data:
{json.dumps(invoice_data, indent=2)}

User Profile:
{json.dumps(user_profile, indent=2)}

Generate a reply that confirms receipt and approval of the invoice."""

        # Create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Get response from LLM
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract and parse JSON from response
            content = response.content
            if isinstance(content, str):
                import re
                # Find JSON content (in case there's additional text)
                start = content.find('{')
                if start != -1:
                    brace_count = 0
                    end = start
                    for i in range(start, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    if brace_count == 0:
                        content = content[start:end]
                        try:
                            reply_data = json.loads(content)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing JSON from LLM response: {e}", exc_info=True)
                            reply_data = {
                                "subject": f"Re: {email_data.get('subject', '')} - Invoice Approved",
                                "body": "We have received and approved your invoice for payment.",
                                "summary": "Invoice approval notification"
                            }
                    else:
                        raise ValueError("Unbalanced JSON braces")
                else:
                    raise ValueError("No JSON content found")

            else:
                reply_data = {
                    "subject": f"Re: {email_data.get('subject', '')} - Invoice Approved",
                    "body": "We have received and approved your invoice for payment.",
                    "summary": "Invoice approval notification"
                }
                
            # Format as email message
            reply_message = self._format_email_reply(
                to=email_data.get("from", ""),
                from_addr=email_data.get("to", ""),
                subject=reply_data.get("subject", f"Re: {email_data.get('subject', '')} - Invoice Approved"),
                body=reply_data.get("body", "")
            )
            
            # Add reply message to reply_data
            reply_data["message"] = reply_message
            
            return reply_data
            
        except Exception as e:
            logger.error(f"Error generating invoice approval: {e}", exc_info=True)
            return {
                "subject": f"Re: {email_data.get('subject', '')} - Invoice Approved",
                "body": "We have received and approved your invoice for payment.",
                "summary": "Error generating approval",
                "error": "An error occurred while generating approval reply."
            }
    
    async def generate_invoice_rejection(self, email_data: Dict[str, Any], invoice_data: Dict[str, Any], reasons: List[str], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an invoice rejection reply.
        
        Args:
            email_data: Dictionary containing email data
            invoice_data: Dictionary containing invoice data
            reasons: List of rejection reasons
            user_profile: Dictionary containing user profile data
            
        Returns:
            Dictionary containing rejection reply
        """
        system_prompt = """You are Dela's invoice rejection reply generator. Your role is to generate appropriate rejection replies for invoices.

Your replies should:
- Confirm receipt of the invoice
- Politely explain why the invoice cannot be approved
- Provide clear instructions on what needs to be corrected
- Be professional and helpful
- Match the user's communication style

Always return valid JSON only with the following structure:
{
    "subject": "Reply subject line",
    "body": "Full email body with greeting and sign-off",
    "summary": "Brief summary of the reply"
}"""

        user_prompt = f"""Generate an invoice rejection reply based on the following:

Original Email:
From: {email_data.get('from', '')}
To: {email_data.get('to', '')}
Subject: {email_data.get('subject', '')}

Invoice Data:
{json.dumps(invoice_data, indent=2)}

Rejection Reasons:
{json.dumps(reasons, indent=2)}

User Profile:
{json.dumps(user_profile, indent=2)}

Generate a reply that politely explains why the invoice cannot be approved and what needs to be corrected."""

        # create messages for the LLM   
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
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
                
                try:
                    reply_data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON from LLM response: {e}", exc_info=True)
                    reply_data = {
                        "subject": f"Re: {email_data.get('subject', '')} - Invoice Requires Attention",
                        "body": "We have received your invoice but cannot approve it at this time.",
                        "summary": "Invoice rejection notification"
                    }
            else:
                reply_data = {
                    "subject": f"Re: {email_data.get('subject', '')} - Invoice Requires Attention",
                    "body": "We have received your invoice but cannot approve it at this time.",
                    "summary": "Invoice rejection notification"
                }
                
            # Format as email message
            reply_message = self._format_email_reply(
                to=email_data.get("from", ""),
                from_addr=email_data.get("to", ""),
                subject=reply_data.get("subject", f"Re: {email_data.get('subject', '')} - Invoice Requires Attention"),
                body=reply_data.get("body", "")
            )
            
            # Add reply message to reply_data
            reply_data["message"] = reply_message
            
            return reply_data
            
        except Exception as e:
            logger.error(f"Error generating invoice rejection: {e}", exc_info=True)
            return {
                "subject": f"Re: {email_data.get('subject', '')} - Invoice Requires Attention",
                "body": "We have received your invoice but cannot approve it at this time.",
                "summary": "Error generating rejection",
                "error": "An error occurred while generating rejection reply."
            }
    
    def _extract_json_from_llm_response(self, response_content: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response content.
        
        Args:
            response_content: Raw response content from LLM
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            json.JSONDecodeError: If JSON parsing fails
            ValueError: If no valid JSON found
        """
        # try direct JSON parsing first
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            pass
    
        # try to find JSON by looking for balanced braces
        start = response_content.find('{')
        if start == -1:
            raise ValueError("No JSON object found in response")
    
        brace_count = 0
        end = start
        for i in range(start, len(response_content)):
            if response_content[i] == '{':
                brace_count += 1
            elif response_content[i] == '}':
                brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break
    
            if brace_count != 0:
                raise ValueError("Unbalanced JSON braces in response")
    
            json_str = response_content[start:end]
            return json.loads(json_str)