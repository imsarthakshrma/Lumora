# ===== SNIPPET 1: Add to gmail.py =====
# Add this method to your GmailMonitor class in gmail.py

async def send_email(self, to_email: str, subject: str, body: str) -> bool:
    """
    Send an email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = self.email_address
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add body
        message.attach(MIMEText(body, "plain"))
        
        # Connect to SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(self.email_address, self.password)
            server.send_message(message)
            
        print(f"Email sent: {subject}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# ===== SNIPPET 2: Modify main.py process_email function =====
# Add this confirmation code to your process_email function in main.py

# After generating the reply but before sending it:
console.print(Panel(
    f"Subject: {reply_data.get('subject')}\n\n"
    f"{reply_data.get('body')}",
    title="Generated Reply"
))

# Ask for confirmation before sending
async def send_email(self, email_data, reply_data, send_reply):
    if send_reply:
        user_input = input("Send this reply? (Y/N): ")
        if user_input.strip().upper() == "Y":
            success = await self.gmail_monitor.send_email(
                to_email=email_data.get('from'),
                subject=reply_data.get('subject'),
                body=reply_data.get('body')
            )
            if success:
                console.print("[green]Reply sent successfully![/green]")
            else:
                console.print("[red]Failed to send reply![/red]")
    else:
        console.print("[yellow]Reply sending cancelled by user[/yellow]")


# ===== SNIPPET 3: Update main.py command line arguments =====
# Modify your main function in main.py to include these options

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
        await app.demo_with_sample_email(send_reply=False)


# ===== SNIPPET 4: Update imports in main.py =====
# Make sure you have these imports at the top of main.py

from integrations.gmail import GmailMonitor  # Use existing gmail.py instead of creating a new module

# And update the GmailMonitor initialization in __init__
self.gmail_monitor = GmailMonitor(
    email_address=os.getenv("GMAIL_EMAIL"),
    password=os.getenv("GMAIL_PASSWORD")
)
