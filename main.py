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
from langchain.chat_models import ChatOpenAI

# Import our agents
from agents.analyser import Analyser
from agents.observer import Observer
from agents.automator import Automator
from knowledge_graph.kg_agent import AsyncKnowledgeGraphAgent
from integrations.gmail_integration import AsyncGmailMonitor

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
        
        # Create knowledge graph agent
        self.kg_agent = AsyncKnowledgeGraphAgent(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )
        
        # Create agents
        self.analyser = Analyser(llm=self.llm)
        self.observer = Observer(kg_agent=self.kg_agent, llm=self.llm)
        self.automator = Automator(observer=self.observer, llm=self.llm)
        
        # Create Gmail monitor
        self.gmail_monitor = AsyncGmailMonitor(
            email=os.getenv("GMAIL_EMAIL"),
            password=os.getenv("GMAIL_PASSWORD")
        )
        
        # User profile (mock data)
        self.user_profile = self._load_user_profile()
        
    def _load_user_profile(self):
        """Load mock user profile data"""
        # In a real app, this would load from a database or file
        return {
            "name": "Alex Johnson",
            "email": os.getenv("GMAIL_EMAIL"),
            "preferences": {
                "communication_style": "professional",
                "response_time": "within 24 hours",
                "signature": "Best regards,\nAlex Johnson\nCEO, Acme Corp"
            },
            "invoice_preferences": {
                "auto_approve_below": 500.00,
                "approved_vendors": ["Office Supplies Inc.", "Tech Solutions", "Marketing Partners"],
                "payment_terms": "net 30",
                "approval_workflow": "auto_below_threshold"
            }
        }
    
    async def process_email(self, email_message: Message, demo_mode=False, send_reply=True):
        """
        Process a single email through the full workflow
        
        Args:
            email_message: Email message to process
            demo_mode: Whether to run in demo mode with extra output
            send_reply: Whether to actually send the reply email
            
        Returns:
            Dictionary containing processing results
        """
        # Create layout for live display
        if demo_mode:
            layout = self._create_demo_layout()
            
            with Live(layout, refresh_per_second=4, console=console):
                # Step 1: Analyse email
                layout["main"].update(Panel("Step 1: Analysing email...", title="Dela AI"))
                email_data = await self.analyser.analyse_email(email_message)
                
                # Update display
                layout["main"].update(Panel(
                    f"Email from: {email_data.get('from')}\n"
                    f"Subject: {email_data.get('subject')}\n\n"
                    f"Intent: {email_data.get('intent')}\n"
                    f"Category: {email_data.get('category')}\n"
                    f"Priority: {email_data.get('priority')}\n",
                    title="Email Analysis"
                ))
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 2: Check if it's an invoice
                is_invoice = await self.analyser.detect_invoice(email_data)
                
                # Step 3: Extract entities for knowledge graph
                layout["main"].update(Panel("Step 2: Extracting knowledge graph data...", title="Dela AI"))
                kg_data = await self.analyser.extract_entities_for_kg(email_data)
                email_data["kg_data"] = kg_data
                
                # Display extracted entities
                entity_table = Table(title="Extracted Entities", box=box.ROUNDED)
                entity_table.add_column("Type")
                entity_table.add_column("Properties")
                
                for entity in kg_data.get("entities", [])[:5]:  # Show first 5 entities
                    entity_type = entity.get("type", "Unknown")
                    props = json.dumps(entity.get("properties", {}), indent=2)
                    entity_table.add_row(entity_type, props)
                
                layout["main"].update(entity_table)
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 4: Update knowledge graph
                layout["main"].update(Panel("Step 3: Updating knowledge graph...", title="Dela AI"))
                await self.observer.observe_email_interaction(email_data)
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Step 5: Generate reply
                layout["main"].update(Panel("Step 4: Generating reply...", title="Dela AI"))
                
                if is_invoice:
                    # Process as invoice
                    result = await self.automator.process_invoice(email_data, self.user_profile)
                    if result.get("success", False):
                        reply_data = result.get("approval_reply", {})
                    else:
                        reply_data = result.get("rejection_reply", {})
                else:
                    # Generate normal reply
                    reply_data = await self.automator.generate_email_reply(email_data, self.user_profile)
                
                # Display reply
                layout["main"].update(Panel(
                    f"Subject: {reply_data.get('subject')}\n\n"
                    f"{reply_data.get('body')}",
                    title="Generated Reply"
                ))
                
                # Step 6: Send reply (if enabled)
                layout["main"].update(Panel("Step 5: Sending reply...", title="Dela AI"))
                
                if send_reply:
                    # Actually send the email
                    success = await self.gmail_monitor.send_email(reply_data["message"])
                    status = "✅ Sent successfully!" if success else "❌ Failed to send"
                else:
                    status = "⚠️ Sending disabled (demo mode)"
                
                # Pause for demo effect
                await asyncio.sleep(2)
                
                # Final summary
                layout["main"].update(Panel(
                    f"Email processing complete!\n\n"
                    f"- Email from {email_data.get('from')} was processed\n"
                    f"- Category: {email_data.get('category')}\n"
                    f"- Reply generated: {reply_data.get('subject')}\n"
                    f"- Reply status: {status}\n"
                    f"- Knowledge graph updated with {len(kg_data.get('entities', []))} entities and "
                    f"{len(kg_data.get('relationships', []))} relationships",
                    title="Processing Complete"
                ))
                
                return reply_data
        else:
            # Non-demo mode, just process without the visual effects
            email_data = await self.analyser.analyse_email(email_message)
            is_invoice = await self.analyser.detect_invoice(email_data)
            kg_data = await self.analyser.extract_entities_for_kg(email_data)
            email_data["kg_data"] = kg_data
            await self.observer.observe_email_interaction(email_data)
            
            if is_invoice:
                result = await self.automator.process_invoice(email_data, self.user_profile)
                if result.get("success", False):
                    reply_data = result.get("approval_reply", {})
                else:
                    reply_data = result.get("rejection_reply", {})
            else:
                reply_data = await self.automator.generate_email_reply(email_data, self.user_profile)
            
            # Send reply if enabled
            if send_reply:
                await self.gmail_monitor.send_email(reply_data["message"])
                console.print(f"[green]Reply sent: {reply_data.get('subject')}[/green]")
            
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
    
    async def demo_with_sample_email(self, send_reply=True):
        """
        Run a demo with a sample email
        
        Args:
            send_reply: Whether to actually send the reply email
        """
        console.print(Panel("Starting Dela AI Email Automation Demo", style="bold green"))
        
        # Create a sample email
        sample_email = MIMEMultipart()
        sample_email["From"] = "vendor@example.com"
        sample_email["To"] = self.user_profile["email"]
        sample_email["Subject"] = "Invoice #INV-2023-456 for Office Supplies"
        sample_email["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        sample_email["Message-ID"] = f"<{datetime.now().timestamp()}@example.com>"
        
        # Email body
        body = """Hello Alex,

Please find attached our invoice #INV-2023-456 for your recent office supplies order.

Invoice Details:
- Invoice Number: INV-2023-456
- Amount: $425.75
- Due Date: August 15, 2025
- Payment Terms: Net 30

Please let me know if you have any questions.

Best regards,
Sarah Johnson
Office Supplies Inc.
"""
        sample_email.attach(MIMEText(body, "plain"))
        
        # Process the sample email
        await self.process_email(sample_email, demo_mode=True, send_reply=send_reply)
    
    async def run_email_monitor(self, send_replies=True):
        """
        Run the email monitor to process real emails
        
        Args:
            send_replies: Whether to actually send reply emails
        """
        console.print(Panel("Starting Dela AI Email Monitor", style="bold green"))
        console.print(f"[yellow]{'✓' if send_replies else '✗'} Auto-reply is {'ENABLED' if send_replies else 'DISABLED'}[/yellow]")
        
        # Define callback for new emails
        async def email_callback(email_message):
            console.print(Panel(f"New email received: {email_message['Subject']}", style="bold blue"))
            await self.process_email(email_message, send_reply=send_replies)
        
        # Start monitoring
        await self.gmail_monitor.connect()
        await self.gmail_monitor.monitor_inbox(callback=email_callback)


async def main():
    """Main entry point"""
    # Create app
    app = DelaApp()
    
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--monitor":
            # Run email monitor (read-only mode)
            await app.run_email_monitor(send_replies=False)
        elif sys.argv[1] == "--monitor-send":
            # Run email monitor with auto-reply enabled
            console.print(Panel("⚠️ WARNING: Auto-reply is ENABLED. Dela will send real emails.", style="bold red"))
            await asyncio.sleep(3)  # Give user time to cancel if needed
            await app.run_email_monitor(send_replies=True)
        elif sys.argv[1] == "--demo-send":
            # Run demo with real email sending
            console.print(Panel("⚠️ WARNING: Demo will send a real email reply.", style="bold red"))
            await asyncio.sleep(3)  # Give user time to cancel if needed
            await app.demo_with_sample_email(send_reply=True)
    else:
        # Run demo without sending emails
        await app.demo_with_sample_email(send_reply=True)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())