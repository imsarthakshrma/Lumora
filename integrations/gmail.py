import asyncio
import email
import imaplib
# import json
import os
# import re
from datetime import datetime
from email.header import decode_header
from typing import Dict, List, Any, Optional, Set

from dotenv import load_dotenv

class GmailMonitor:
    """
    GmailMonitor is a monitor that uses IMAP to check for new emails. 
    """
    def __init__(self, email_address: str = None, password: str = None):

        """Initialize the gmail monitor with credentials"""

        load_dotenv()

        self.email_address = email_address or os.getenv("GMAIL_EMAIL")
        self.password = password or os.getenv("GMAIL_PASSWORD")
        self.imap_server = "imap.gmail.com"
        self.processed_emails: Set[str] = set()  # track processed email IDs


    async def connect(self) -> None:
        """Asynchronous connection to Gmail IMAP server"""
        if hasattr(self, 'mail'):
            raise ValueError("Already connected to IMAP server")
        else:
            self.mail = await asyncio.to_thread(self._connect_sync)

    def _connect_sync(self) -> imaplib.IMAP4_SSL:
        """Synchronous connection to Gmail IMAP server"""
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_address, self.password)
        return mail

    async def disconnect(self) -> None:
        """Disconnect from the IMAP server"""
        if hasattr(self, 'mail'):
            await asyncio.to_thread(self.mail.logout)
        else:
            raise ValueError("Not connected to IMAP server")
    
    async def fetch_emails(self, folder: str = "INBOX", search_criteria: str = "UNSEEN") -> List[Dict[str, Any]]:
        """Fetch emails from the specified folder that match the search criteria"""
        # select the mailbox/folder
        await asyncio.to_thread(self.mail.select, folder)

        # search for emails that matches the criteria
        status, messages = await asyncio.to_thread(self.mail.search, None, search_criteria)
        
        if status !="OK":
            print(f"Error searching for emails: {status}")
            return []
        
        # get the list of email IDs
        email_ids = messages[0].split()
        
        # fetch the emails
        emails = []
        for email_id in email_ids:
            # skip already processed emails
            if email_id in self.processed_emails:
                continue
            
            emails_data = await self._fetch_emails(email_id)
            if emails_data:
                emails.append(emails_data)
                self.processed_emails.add(email_id.decode())
        
        return emails

    async def _fetch_email(self, email_id: bytes) ->  Optional[Dict[str, Any]]:
        """Fetch a single email by ID"""
        try:
            # fetch the email data
            status, data = await asyncio.to_thread(self.mail.fetch, email_id, '(RFC822)')

            if status != "OK":
                print(f"Error fetching email: {status}")
                return None

            # parse the email data
            email_data = data[0][1]
            msg = email.message_from_bytes(email_data)

            # extract email metadata
            subject = self._decode_header(msg['Subject'])
            from_addr = self._decode_header(msg['From'])
            to_addr = self._decode_header(msg['To'])
            date_str = self._decode_header(msg['Date'])

            # parse the date
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except Exception as e:
                date = datetime.now()

            # extract the body
            body = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get_content_disposition()          

                    # extract the content
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="ignore")
                    
                    # extract attachments
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            # decode the filename if needed
                            filename = self._decode_header(filename)
                            
                            # get attachment data
                            attachment_data = part.get_payload(decode=True)
                            
                            attachments.append({
                                "filename": filename,
                                "content_type": content_type,
                                "size": len(attachment_data) if attachment_data else 0
                            })
            
            else:
                # not multipart - get the content directly
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")

            # create the email data dictionary
            email_data = {
                "id": email_id.decode(),
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date.isoformat(),
                "body": body,
                "attachments": attachments,
                "has_invoice": self._check_for_invoice(subject, body, attachments)
            }

            return email_data

        except Exception as e:
            print(f"Error fetching email: {e}")
            return None

    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        
        decoded_header = decode_header(header)
        header_parts = []

        for content, encoding in decoded_header:
            if isinstance(content, bytes):
                # if the encoding is specified, use it; otherwise, try utf-8
                if encoding:
                    header_parts.append(content.decode(encoding, errors="ignore"))
                else:
                    header_parts.append(content.decode("utf-8", errors="ignore"))
            else:
                header_parts.append(content)
        
        return "".join(header_parts)
        
        
    def _check_for_invoice(self, subject: str, body: str, attachments: List[Dict[str, Any]]) -> bool:
        """Check if the email contains an invoice"""
        # check the subject
        subject_lower = subject.lower()
        if any(keyword in subject_lower for keyword in ["invoice", "bill", "payment", "receipt"]):
            return True
        
        # check the body
        body_lower = body.lower()
        if any(keyword in body_lower for keyword in ["invoice", "bill", "payment", "receipt", "amount due", "total due"]):
            return True
        
        # check attachments
        for attachment in attachments:
            filename = attachment["filename"].lower()
            if any(keyword in filename for keyword in ["invoice", "bill", "payment", "receipt"]):
                return True
            
            # check for PDF files (common format for invoices)
            if filename.endswith(".pdf"):
                return True
        
        return False

    async def mark_as_read(self, email_id: str) -> None:
        """Mark an email as read"""
        await asyncio.to_thread(self.mail.store, email_id, "+FLAGS", "\\Seen")
    
    async def monitor_inbox(self, callback, interval: int = 60, folder: str = "INBOX") -> None:
        """
        Monitor the inbox for new emails at regular intervals
        
        Args:
            callback: Async function to call with new emails
            interval: Check interval in seconds
            folder: Email folder to monitor
        """
        while True:
            try:
                # connect to Gmail
                await self.connect()
                
                # fetch new emails
                emails = await self.fetch_emails(folder=folder)
                
                # filter for invoice emails
                invoice_emails = [email for email in emails if email["has_invoice"]]
                
                if invoice_emails:
                    # process the emails with the callback
                    await callback(invoice_emails)
                
                # disconnect
                await self.disconnect()
                
            except Exception as e:
                print(f"Error monitoring inbox: {e}")
            
            # wait for the next check
            await asyncio.sleep(interval)