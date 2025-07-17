# Dela AI Email Automation - Live Demo Instructions

## Setup Requirements

1. **Gmail Account Setup**
   - You need a Gmail account for Dela to use
   - Enable "Less secure app access" or create an App Password in your Google Account settings
   - Add these credentials to your `.env` file:
     ```
     GMAIL_EMAIL=your.email@gmail.com
     GMAIL_PASSWORD=your-password-or-app-password
     ```

2. **Neo4j Setup**
   - Ensure your Neo4j database is running
   - Add connection details to your `.env` file:
     ```
     NEO4J_URI=bolt://localhost:7687
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=your-password
     ```

3. **OpenAI API Key**
   - Add your OpenAI API key to your `.env` file:
     ```
     OPENAI_API_KEY=your-api-key
     ```

## Running the Live Demo

### Option 1: Demo Mode with Email Sending

This mode uses a sample invoice email and will send a real reply:

```bash
python main.py --demo-send
```

### Option 2: Live Email Monitoring with Auto-Reply

This mode will monitor your inbox for new emails and process them in real-time:

```bash
python main.py --monitor-send
```

## Demo Flow

1. **Start the Demo**
   - Run the command: `python main.py --demo-send`
   - You'll see a warning that real emails will be sent
   - The demo will initialize and show the Dela AI interface

2. **Email Analysis**
   - The demo will analyze the sample invoice email
   - You'll see extracted metadata, intent, and category

3. **Knowledge Graph Integration**
   - Entities and relationships will be extracted
   - The knowledge graph will be updated

4. **Reply Generation**
   - Dela will generate an appropriate reply based on the email content
   - For invoices, it will check against user preferences

5. **Confirmation Step**
   - You'll be prompted with: `Send this reply? (Y/N):`
   - Type `Y` to send the actual email or `N` to cancel

6. **Email Sending**
   - If confirmed, Dela will send the email via your Gmail account
   - You'll see a success or failure message

## Tips for a Successful Demo

1. **Test Before the Live Demo**
   - Send yourself a test email first to make sure everything works

2. **Prepare a Script**
   - Have a narrative ready to explain what Dela is doing at each step

3. **Show the Received Email**
   - Have another device or browser window open to show the received email

4. **Highlight Key Features**
   - Knowledge graph learning
   - Invoice auto-approval based on user preferences
   - Natural language reply generation

5. **Troubleshooting**
   - If emails aren't sending, check your Gmail security settings
   - Make sure your `.env` file has the correct credentials
   - Verify that the SMTP port (587) isn't blocked by your firewall
