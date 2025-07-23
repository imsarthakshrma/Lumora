import os
import asyncio
import json
from datetime import datetime
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.live import Live
from rich.layout import Layout
# from rich.progress import Progress, SpinnerColumn, TextColumn
from langchain_openai import ChatOpenAI

# Import our agents
from agents.analyser import Analyser
from agents.observer import Observer
from agents.automator import Automator
from knowledge_graph.kg_agent import AsyncKnowledgeGraph,AsyncKnowledgeGraphAgent
from integrations.gmail import GmailMonitor
# from rag.graph_rag import GraphRAG
# from langchain.memory import ConversationBufferMemory



# Load environment variables
load_dotenv()

# Rich console for pretty output
console = Console()

class DelaApp:
    """
    Main application class for Dela POC that orchestrates all components.
    """
    
    def __init__(self):
        """Initialize the Dela application"""
        # Initialize components
        self.llm = ChatOpenAI(
            temperature=0.1,
            model="gpt-4o",
        )
        
        self.kg = AsyncKnowledgeGraph(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )

        # Then create the agent using the knowledge graph
        self.kg_agent = AsyncKnowledgeGraphAgent(knowledge_graph=self.kg)
        
        # Create agents
        self.analyser = Analyser(llm=self.llm)
        self.observer = Observer(kg_agent=self.kg_agent, llm=self.llm)
        self.automator = Automator(observer=self.observer, llm=self.llm)
        
        # Create Gmail monitor
        self.gmail_monitor = GmailMonitor(
            email_address=os.getenv("GMAIL_EMAIL"),
            password=os.getenv("GMAIL_PASSWORD")
        )
        
        # Create memory
        # self.memory = ConversationBufferMemory(memory_key="chat_history")
        
        # User profile (mock data)
        self.user_profile = self._load_user_profile()
        
        
    def _load_user_profile(self):
        """Load mock user profile data"""
        # In a real app, this would load from a database or file
        return {
            "name": "Richard Hendricks",
            "email": os.getenv("GMAIL_EMAIL"),
            "preferences": {
                "communication_style": "professional",
                "response_time": "within 24 hours",
                "signature": "Best regards,\nRichard Hendricks\nCEO, Pied Piper"
            },
            "invoice_preferences": {
                "auto_approve_below": 500.00,
                "approved_vendors": ["Office Supplies Inc.", "Tech Solutions", "Marketing Partners"],
                "payment_terms": "net 30",
                "approval_workflow": "auto_below_threshold"
            }
        }
    
    async def process_email(self, email_message, demo_mode=False, send_reply=False):
        """
        Process an email message
        
        Args:
            email_message: Email message to process
            demo_mode: Whether to run in demo mode with visual feedback
            send_reply: Whether to actually send the reply email
            
        Returns:
            Dictionary containing reply data
        """
        if demo_mode:
            # Demo mode with visual feedback
            layout = self._create_demo_layout()
            
            with Live(layout, refresh_per_second=4) as live:
                # Step 0: Interactive Email Preview
                layout["main"].update(Panel("📧 New Email Received - Analyzing...", title="Dela AI"))
                
                # Quick analysis for preview
                email_data = await self.analyser.analyse_email(email_message)
                is_invoice = await self.analyser.detect_invoice(email_data)
                
                # Show email preview
                layout["main"].update(Panel(
                    f"📧 New Email Received:\n\n"
                    f"From: {email_data.get('from')}\n"
                    f"Subject: {email_data.get('subject')}\n"
                    f"Category: {email_data.get('category', 'General')}\n"
                    f"Urgency: {email_data.get('urgency', 'Normal')}\n\n"
                    f"Preview: {email_data.get('content', '')[:200]}...\n\n"
                    f"Preparing smart suggestions...",
                    title="📬 Email Preview"
                ))
                
                await asyncio.sleep(2)
                
                # Generate smart suggestions based on email type
                if is_invoice:
                    suggestion_text = f"""🤖 I noticed you received an invoice from {email_data.get('from', 'Unknown Sender')}.

Based on your past behavior, you typically:
• Verify the invoice details and authenticity
• Match it with purchase orders in your system
• Approve payment if under your threshold
• Record the transaction for accounting
• Archive the invoice for future reference

Would you like me to handle this invoice for you?

Options:
1. Yes, process it automatically
2. Yes, but let me review before any actions
3. No, I'll handle this manually"""
                else:
                    suggestion_text = f"""🤖 I noticed you received an email from {email_data.get('from', 'Unknown Sender')}.

Based on the content, this appears to be a {email_data.get('category', 'general')} email.

I can help you by:
• Analyzing the content and intent
• Generating an appropriate response
• Updating your knowledge graph with relevant information
• Sending a professional reply

Would you like me to handle this email for you?

Options:
1. Yes, process it automatically
2. Yes, but let me review the reply before sending
3. No, I'll handle this manually"""
                
                layout["main"].update(Panel(
                    suggestion_text,
                    title="🧠 Smart Suggestions"
                ))
                
                await asyncio.sleep(1)
                
            # Exit Live context for user input
            console.clear()
            console.print(f"[bold blue]📧 New Email Received:[/bold blue]")
            console.print(f"[yellow]From:[/yellow] {email_data.get('from')}")
            console.print(f"[yellow]Subject:[/yellow] {email_data.get('subject')}")
            console.print(f"[yellow]Category:[/yellow] {email_data.get('category', 'General')}")
            console.print()
            
            if is_invoice:
                console.print(f"[bold green]🤖 Smart Suggestion:[/bold green]")
                console.print(f"I noticed this is an invoice. Based on your patterns, I can:")
                console.print(f"• Verify and process the invoice")
                console.print(f"• Generate appropriate approval/rejection response")
                console.print(f"• Update your knowledge graph")
                console.print()
                console.print(f"[bold cyan]Options:[/bold cyan]")
                console.print(f"1. Process automatically")
                console.print(f"2. Process with review")
                console.print(f"3. Skip automation")
            else:
                console.print(f"[bold green]🤖 Smart Suggestion:[/bold green]")
                console.print(f"I can analyze this email and generate a professional response.")
                console.print()
                console.print(f"[bold cyan]Options:[/bold cyan]")
                console.print(f"1. Process automatically")
                console.print(f"2. Process with review")
                console.print(f"3. Skip automation")
            
            console.print()
            user_choice = input("What would you like me to do? (1/2/3): ").strip()
            
            if user_choice == "3":
                console.print("[yellow]Automation skipped. Email remains unprocessed.[/yellow]")
                return {"skipped": True, "reason": "User chose manual handling"}
            
            # Determine if user wants review
            review_mode = (user_choice == "2")
            
            # Continue with processing
            with Live(layout, refresh_per_second=4) as live:
                # Step 1: Extract email data
                layout["main"].update(Panel("Step 1: Extracting email data...", title="Dela AI"))
                email_data = await self.analyser.analyse_email(email_message)
                
                # Display email data
                layout["main"].update(Panel(
                    f"From: {email_data.get('from')}\n"
                    f"Subject: {email_data.get('subject')}\n\n"
                    f"{email_data.get('content')[:300]}...",
                    title="Email Data"
                ))
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 2: Analyze content
                layout["main"].update(Panel("Step 2: Analyzing content...", title="Dela AI"))
                is_invoice = await self.analyser.detect_invoice(email_data)
                
                # Display analysis
                layout["main"].update(Panel(
                    f"Category: {email_data.get('category')}\n"
                    f"Intent: {email_data.get('intent')}\n"
                    f"Is Invoice: {'Yes' if is_invoice else 'No'}\n"
                    f"Sentiment: {email_data.get('sentiment')}\n"
                    f"Urgency: {email_data.get('urgency')}",
                    title="Content Analysis"
                ))
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 3: Extract entities for knowledge graph
                layout["main"].update(Panel("Step 3: Extracting knowledge graph entities...", title="Dela AI"))
                kg_data = await self.analyser.extract_entities_for_kg(email_data)
                email_data["kg_data"] = kg_data
                
                # Display KG data
                entities_text = ""
                for e in kg_data.get("entities", [])[:5]:
                    entity_type = e.get('type', 'Unknown')
                    # Try to get a name from properties, or use the first property value as identifier
                    properties = e.get('properties', {})
                    if properties:
                        if 'name' in properties:
                            entity_name = properties.get('name')
                        elif 'id' in properties:
                            entity_name = properties.get('id')
                        else:
                            # Use the first property value
                            first_key = next(iter(properties), None)
                            entity_name = properties.get(first_key, 'Unknown')
                    else:
                        entity_name = 'Unknown'
                    
                    entities_text += f"- {entity_type}: {entity_name}\n"
                
                if len(kg_data.get("entities", [])) > 5:
                    entities_text += f"- ... and {len(kg_data.get('entities', [])) - 5} more"
                
                layout["main"].update(Panel(
                    f"Entities Extracted:\n{entities_text}",
                    title="Knowledge Graph Data"
                ))
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 4: Update knowledge graph
                layout["main"].update(Panel("Step 4: Updating knowledge graph...", title="Dela AI"))
                try:
                    await self.observer.observe_email_interaction(email_data)
                except Exception as e:
                    console.print(f"[yellow]Warning: Knowledge graph update encountered an issue: {str(e)}[/yellow]")
                    # Continue processing even if knowledge graph update fails
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 5: Generate reply
                layout["main"].update(Panel("Step 5: Generating reply...", title="Dela AI"))
                
                if is_invoice:
                    # Process as invoice
                    result = await self.automator.process_invoice(email_data, self.user_profile)
                    if result.get("success", False):
                        reply_data = result.get("approval_reply", {})
                        # Ensure reply_data has valid subject and body
                        if not reply_data.get("subject"):
                            reply_data["subject"] = f"Re: {email_data.get('subject', '')} - Invoice Approved"
                        if not reply_data.get("body"):
                            # Generate LLM response instead of static template
                            llm_response = await self._generate_llm_email_reply(
                                email_data, 
                                reply_type="invoice_approval"
                            )
                            reply_data["subject"] = llm_response["subject"]
                            reply_data["body"] = llm_response["body"]
                        
                        # Ensure message key exists for email sending
                        if "message" not in reply_data or reply_data["message"] is None:
                            # Format email message using automator's method
                            reply_data["message"] = self.automator._format_email_reply(
                                to=email_data.get("from", ""),
                                from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                                subject=reply_data["subject"],
                                body=reply_data["body"]
                            )
                    else:
                        reply_data = result.get("rejection_reply", {})
                        # Ensure reply_data has valid subject and body
                        if not reply_data.get("subject"):
                            reply_data["subject"] = f"Re: {email_data.get('subject', '')} - Invoice Requires Attention"
                        if not reply_data.get("body"):
    # Generate LLM response instead of static template
                            llm_response = await self._generate_llm_email_reply(
                                email_data, 
                                reply_type="invoice_rejection"
                            )
                            reply_data["subject"] = llm_response["subject"]
                            reply_data["body"] = llm_response["body"]
                        
                        # Ensure message key exists for email sending
                        if "message" not in reply_data or reply_data["message"] is None:
                            # Format email message using automator's method
                            reply_data["message"] = self.automator._format_email_reply(
                                to=email_data.get("from", ""),
                                from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                                subject=reply_data["subject"],
                                body=reply_data["body"]
                            )

# Thank you for your email regarding the invoice submission.

# We have received and carefully reviewed your invoice. However, we are unable to approve it for payment at this time due to one or more of the following reasons:

# • Missing or incomplete information
# • Documentation requirements not met
# • Invoice details require clarification
# • Additional approval processes needed

# Please review your submission and feel free to resubmit with any necessary corrections or additional documentation. If you have any questions about the specific requirements, please don't hesitate to contact us for clarification.

# We appreciate your understanding and look forward to resolving this matter promptly.

# Best regards,

# Dela AI
# On behalf of {sender_name}

# ---
# This email was generated by Dela AI Email Automation System"""
                        
                        # Ensure message key exists for email sending
                        if "message" not in reply_data or reply_data["message"] is None:
                            # Format email message using automator's method
                            reply_data["message"] = self.automator._format_email_reply(
                                to=email_data.get("from", ""),
                                from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                                subject=reply_data["subject"],
                                body=reply_data["body"]
                            )
                else:
                    # Generate normal reply
                    reply_data = await self.automator.generate_email_reply(email_data, self.user_profile)
                    # Ensure reply_data has valid subject and body
                    if not reply_data.get("subject"):
                        reply_data["subject"] = f"Re: {email_data.get('subject', '')}"
                    if not reply_data.get("body"):
                        reply_data["body"] = "Thank you for your email. We will get back to you soon."
                    
                    # Ensure message key exists for email sending
                    if "message" not in reply_data or reply_data["message"] is None:
                        # Format email message using automator's method
                        reply_data["message"] = self.automator._format_email_reply(
                            to=email_data.get("from", ""),
                            from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                            subject=reply_data["subject"],
                            body=reply_data["body"]
                        )
                
                # Display reply
                layout["main"].update(Panel(
                    f"Subject: {reply_data.get('subject')}\n\n"
                    f"{reply_data.get('body')}",
                    title="Generated Reply"
                ))
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 6: Send reply (if enabled)
                layout["main"].update(Panel("Step 6: Preparing to send reply...", title="Dela AI"))
                
                if send_reply and reply_data.get("subject") and reply_data.get("body"):
                    # Only ask for confirmation if user chose review mode or if send_reply is True
                    if review_mode or user_choice == "2":
                        # Clear screen and show email for confirmation
                        console.clear()
                        console.print(f"[bold blue] Email Ready to Send:[/bold blue]")
                        console.print(f"[yellow]To:[/yellow] {email_data.get('from', '')}")
                        console.print(f"[yellow]Subject:[/yellow] {reply_data['subject']}")
                        console.print(f"[yellow]Body:[/yellow]\n{reply_data['body']}")
                        console.print()
                        
                        # Wait for user input
                        user_input = input("Send this email? (Y/N): ").strip().upper()
                        
                        if user_input == "Y":
                            console.print("[green]Sending email...[/green]")
                            try:
                                # Send to the specified recipient email
                                success = await self.gmail_monitor.send_email(
                                    to_email=email_data.get("from", ""),
                                    subject=reply_data["subject"],
                                    body=reply_data["body"]
                                )
                                status = "✅ Sent successfully!" if success else "❌ Failed to send"
                            except Exception as e:
                                status = f" Failed to send: {str(e)}"
                        else:
                            status = " Email sending cancelled by user"
                    elif user_choice == "1":
                        # Automatic processing - send without confirmation
                        console.print("Sending email automatically...")
                        try:
                            success = await self.gmail_monitor.send_email(
                                to_email=email_data.get("from", ""),
                                subject=reply_data["subject"],
                                body=reply_data["body"]
                            )
                            status = "✅ Sent automatically!" if success else "❌ Failed to send"
                        except Exception as e:
                            status = f" Failed to send: {str(e)}"
                    else:
                        status = " Email prepared but not sent"
                elif send_reply:
                    status = "Failed to send: Missing subject or body"
                else:
                    status = "Sending disabled (demo mode)"
            
            # Show final summary
            with Live(self._create_demo_layout(), refresh_per_second=4) as live:
                layout = live.renderable
                # Final summary
                layout["main"].update(Panel(
                    f" Dela AI Processing Complete!\n\n"
                    f" Email from {email_data.get('from')} processed successfully\n"
                    f" Category: {email_data.get('category')}\n"
                    f" Reply generated: {reply_data.get('subject')}\n"
                    f" Reply status: {status}\n"
                    f" Knowledge graph updated with {len(kg_data.get('entities', []))} entities and "
                    f" {len(kg_data.get('relationships', []))} relationships\n\n"
                    f" All systems operational!",
                    title="Processing Complete"
                ))
                
                # Keep the summary visible for a moment
                await asyncio.sleep(10) # Keep the summary visible for 10 seconds
                
            return reply_data
        else:
            # Non-demo mode, just process without the visual effects
            email_data = await self.analyser.analyse_email(email_message)
            is_invoice = await self.analyser.detect_invoice(email_data)
            kg_data = await self.analyser.extract_entities_for_kg(email_data)
            email_data["kg_data"] = kg_data
            try:
                await self.observer.observe_email_interaction(email_data)
            except Exception as e:
                console.print(f"[yellow]Warning: Knowledge graph update encountered an issue: {str(e)}[/yellow]")
                # Continue processing even if knowledge graph update fails
            
            if is_invoice:
                result = await self.automator.process_invoice(email_data, self.user_profile)
                if result.get("success", False):
                    reply_data = result.get("approval_reply", {})
                    # Ensure reply_data has valid subject and body
                    if not reply_data.get("subject"):
                        reply_data["subject"] = f"Re: {email_data.get('subject', '')} - Invoice Approved"
                    if not reply_data.get("body"):
                        llm_response = await self._generate_llm_email_reply(
                            email_data, 
                            reply_type="invoice_approval"
                        )
                        reply_data["subject"] = llm_response["subject"]
                        reply_data["body"] = llm_response["body"]
                        
                    # Ensure message key exists for email sending
                    if "message" not in reply_data or reply_data["message"] is None:
                        # Format email message using automator's method
                        reply_data["message"] = self.automator._format_email_reply(
                            to=email_data.get("from", ""),
                            from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                            subject=reply_data["subject"],
                            body=reply_data["body"]
                        )
                else:
                    reply_data = result.get("rejection_reply", {})
                    # Ensure reply_data has valid subject and body
                    if not reply_data.get("subject"):
                        reply_data["subject"] = f"Re: {email_data.get('subject', '')} - Invoice Requires Attention"
                    if not reply_data.get("body"):
                        llm_response = await self._generate_llm_email_reply(
                            email_data, 
                            reply_type="invoice_rejection"
                        )
                        reply_data["subject"] = llm_response["subject"] 
                        reply_data["body"] = llm_response["body"]

# Thank you for your email regarding the invoice submission.

# We have received and carefully reviewed your invoice. However, we are unable to approve it for payment at this time due to one or more of the following reasons:

# • Missing or incomplete information
# • Documentation requirements not met
# • Invoice details require clarification
# • Additional approval processes needed

# Please review your submission and feel free to resubmit with any necessary corrections or additional documentation. If you have any questions about the specific requirements, please don't hesitate to contact us for clarification.

# We appreciate your understanding and look forward to resolving this matter promptly.

# Best regards,

# Dela AI
# On behalf of {sender_name}

# ---
# This email was generated by Dela AI Personal Assistant"""
                        
                    # Ensure message key exists for email sending
                    if "message" not in reply_data or reply_data["message"] is None:
                        # Format email message using automator's method
                        reply_data["message"] = self.automator._format_email_reply(
                            to=email_data.get("from", ""),
                            from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                            subject=reply_data["subject"],
                            body=reply_data["body"]
                        )
            else:
                # Generate normal reply
                reply_data = await self.automator.generate_email_reply(email_data, self.user_profile)
                # Ensure reply_data has valid subject and body
                if not reply_data.get("subject"):
                    reply_data["subject"] = f"Re: {email_data.get('subject', '')}"
                if not reply_data.get("body"):
                    reply_data["body"] = "Thank you for your email. We will get back to you soon."
                
                # Ensure message key exists for email sending
                if "message" not in reply_data or reply_data["message"] is None:
                    # Format email message using automator's method
                    reply_data["message"] = self.automator._format_email_reply(
                        to=email_data.get("from", ""),
                        from_addr=self.user_profile.get("email", "nativeintel.ni@gmail.com"),
                        subject=reply_data["subject"],
                        body=reply_data["body"]
                    )
            
            # Send reply if enabled
            if send_reply:
                # Check if reply_data has the required fields
                if reply_data.get("subject") and reply_data.get("body"):
                    try:
                        await self.gmail_monitor.send_email(
                            to_email=email_data.get("from", ""),
                            subject=reply_data["subject"],
                            body=reply_data["body"]
                        )
                        console.print(f"[green]Reply sent: {reply_data.get('subject')}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error sending email: {str(e)}[/red]")
                else:
                    console.print("[red]Error: Missing subject or body[/red]")
            
            return reply_data
    
    def _create_demo_layout(self):
        """Create layout for demo mode"""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        # Set up header
        layout["header"].update(Panel("DELA AI EMAIL AUTOMATION", style="bold blue"))
        
        # Set up footer
        layout["footer"].update(Panel("Processing email...", style="italic"))
        
        return layout
    
    async def demo_with_sample_email(self, send_reply: bool = False):
        """
        Run a demo with a sample email
        
        Args:
            send_reply: Whether to actually send the reply email
        """
        await self.gmail_monitor.connect()
        # Initialize the knowledge graph agent
        await self.kg_agent.initialize()
        
        console.print(Panel("Starting Dela AI Demo", style="bold green"))
        
        # Create a sample email
        sample_email = MIMEMultipart()
        sample_email["From"] = "nativeintel.ni@gmail.com"
        sample_email["To"] = "richard@piedpiper.com"
        sample_email["Subject"] = "Invoice #INV-2023-456 for Office Supplies"
        sample_email["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        sample_email["Message-ID"] = f"<{datetime.now().timestamp()}@example.com>"
        
        # Email body
        body = """Hello Richard,

        Please find attached our invoice #INV-2025-318 for your recent office supplies order.

        Invoice Details:
        - Invoice Number: INV-2025-318
        - Amount: $425.75
        - Due Date: August 18, 2025
        - Payment Terms: Net 30

        Please let me know if you have any questions.

        Best regards,
        Sarah Johnson
        Office Supplies Inc.

        """
        sample_email.attach(MIMEText(body, "plain"))
        
        # process the sample email
        await self.process_email(sample_email, demo_mode=True, send_reply=send_reply)
    
    async def run_email_monitor(self, send_replies=True):
        """
        Run the email monitor to process real emails
        
        Args:
            send_replies: Whether to actually send reply emails
        """
        await self.kg_agent.initialize()
        console.print(Panel("Starting Dela AI Email Monitor", style="bold green"))
        console.print(f"[yellow]{'✓' if send_replies else '✗'} Auto-reply is {'ENABLED' if send_replies else 'DISABLED'}[/yellow]")
        
        # define callback for new emails
        async def email_callback(email_message):
            console.print(Panel(f"New email received: {email_message['Subject']}", style="bold blue"))
            await self.process_email(email_message, send_reply=send_replies)
        
        # start monitoring
        await self.gmail_monitor.connect()
        await self.gmail_monitor.monitor_inbox(callback=email_callback)

    async def _generate_llm_email_reply(self, email_data, reply_type="general", invoice_decision=None):
        """
        Generate email reply using LLM based on context and email data
        
        Args:
            email_data: Original email data
            reply_type: Type of reply ("invoice_approval", "invoice_rejection", "general")
            invoice_decision: Decision details for invoices
        
        Returns:
            Dictionary with subject and body
        """
        
        # Prepare context for LLM
        sender_name = self.user_profile.get("name", "User")
        sender_email = self.user_profile.get("email", "")
        communication_style = self.user_profile.get("preferences", {}).get("communication_style", "professional")
        
        # Base system prompt
        system_prompt = f"""You are Dela AI, an intelligent email assistant acting on behalf of {sender_name}.

    Your role is to generate professional, contextually appropriate email responses that match the user's communication style: {communication_style}.

    Key guidelines:
    - Always be professional and courteous
    - Match the tone and urgency of the original email
    - Include relevant details from the original email
    - Sign emails as "Dela AI on behalf of {sender_name}"
    - Keep responses concise but complete
    - Use proper business email formatting
    """

        # Prepare email context
        original_email_context = f"""
    Original Email Details:
    - From: {email_data.get('from', 'Unknown')}
    - Subject: {email_data.get('subject', 'No subject')}
    - Content: {email_data.get('content', '')[:500]}...
    - Category: {email_data.get('category', 'General')}
    - Sentiment: {email_data.get('sentiment', 'Neutral')}
    - Urgency: {email_data.get('urgency', 'Normal')}
    """

        if reply_type == "invoice_approval":
            user_prompt = f"""{original_email_context}

    Task: Generate a professional invoice approval email.

    The invoice has been reviewed and APPROVED for payment. Include:
    - Acknowledgment of receipt
    - Confirmation of approval
    - Expected payment timeline
    - Contact information for questions
    - Professional closing

    Generate both subject and body for the email response."""

        elif reply_type == "invoice_rejection":
            user_prompt = f"""{original_email_context}

    Task: Generate a professional invoice rejection email.

    The invoice has been reviewed but CANNOT BE APPROVED at this time. Include:
    - Acknowledgment of receipt
    - Clear but diplomatic explanation
    - Specific reasons (missing info, documentation issues, etc.)
    - Steps for resubmission
    - Offer to help resolve issues
    - Professional closing

    Generate both subject and body for the email response."""

        else:  # general email
            user_prompt = f"""{original_email_context}

    Task: Generate an appropriate professional email response.

    Analyze the original email and provide a helpful, relevant response that:
    - Addresses the sender's main points or questions
    - Provides useful information or next steps
    - Maintains professional tone
    - Shows understanding of their needs

    Generate both subject and body for the email response."""

        try:
            # Call LLM to generate response
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse the response to extract subject and body
            content = response.content
            
            # Try to extract structured response
            if "Subject:" in content and "Body:" in content:
                parts = content.split("Body:", 1)
                subject_part = parts[0].replace("Subject:", "").strip()
                body_part = parts[1].strip()
            else:
                # Fallback parsing
                lines = content.split('\n')
                subject_part = lines[0] if lines else "Re: " + email_data.get('subject', '')
                body_part = '\n'.join(lines[1:]) if len(lines) > 1 else content
            
            return {
                "subject": subject_part,
                "body": body_part
            }
            
        except Exception as e:
            print(f"Error generating LLM email: {e}")
            # Fallback to simple response
            return {
                "subject": f"Re: {email_data.get('subject', '')}",
                "body": f"Thank you for your email. We have received your message and will respond appropriately.\n\nBest regards,\nDela AI\nOn behalf of {sender_name}"
            }


async def main():
    """Main entry point"""
    # Create app
    app = DelaApp()
    
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--monitor":
            # run email monitor (read-only mode)
            await app.run_email_monitor(send_replies=False)
        elif sys.argv[1] == "--monitor-send":
            # run email monitor with auto-reply enabled
            # console.print(Panel("⚠️ WARNING: Auto-reply is ENABLED. Dela will send real emails.", style="bold red"))
            # await asyncio.sleep(3)  # Give user time to cancel if needed
            await app.run_email_monitor(send_replies=True)
        elif sys.argv[1] == "--demo-send":
            # run demo with real email sending
            # console.print(Panel("⚠️ WARNING: Demo will send a real email reply.", style="bold red"))
            # await asyncio.sleep(3)  # Give user time to cancel if needed
            await app.demo_with_sample_email(send_reply=True)
    else:
        # run demo without sending emails
        await app.demo_with_sample_email(send_reply=True)


if __name__ == "__main__":
    # run the async main function
    asyncio.run(main())