# Lumora Interactive Demo

## Overview

This repository contains a proof-of-concept demonstration of Lumora, an AI agent that learns from user behavior and automates repetitive tasks. The demo showcases how Lumora observes, learns, and automates tasks using GraphRAG (Graph-enhanced Retrieval Augmented Generation) and Knowledge Graph techniques.

## Demo Scenarios

### Scene 1: Morning Routine

**Lumora:** "Good morning! I notice it's Monday at 9:00 AM. Would you like me to generate the weekly sales report now? This typically takes you about 45 minutes, but I can automate it for you."

**User:** "Yes, please go ahead."

**Lumora:** "Generating weekly sales report... I'm gathering data from Salesforce, analyzing the metrics, and creating visualizations comparing to last week's performance."

**[Progress bar fills]**

**Lumora:** "Report completed! I've formatted it using your preferred template and distributed it to the sales team and executives. This saved you 45 minutes. Would you like to review it before I move on?"

**User:** "No, that looks good. Thanks."

### Scene 2: New Task Detection

**[User receives an email]**

**Lumora:** "I noticed you received an invoice from Acme Corp. Based on your past behavior, you typically:
1. Verify the invoice details
2. Match it with purchase orders in the ERP system
3. Approve the payment if under $5,000
4. Record the transaction in QuickBooks
5. Archive the invoice

Would you like me to handle this for you?"

**User:** "Yes, but I want to review it before payment approval."

**Lumora:** "Understood. I'll process steps 1-2, pause for your review, then complete steps 4-5 after your approval."

**[Processing animation]**

**Lumora:** "I've verified the invoice details and matched it with PO #38291 in the ERP system. The amount is $3,450.75 and everything looks consistent with our records. Would you like to approve the payment now?"

**User:** "Yes, approve it."

**Lumora:** "Payment approved. I've recorded the transaction in QuickBooks and archived the invoice in the finance archive. This task would have taken you approximately 32 minutes."

### Scene 3: Knowledge Graph Exploration

**User:** "Lumora, what do you know about our weekly reporting process?"

**[Lumora displays a knowledge graph visualization]**

**Lumora:** "Based on observing your work patterns, I've learned that:
- Weekly reports are generated every Monday morning
- They require data from Salesforce, specifically the weekly_sales report
- You typically analyze revenue, conversion rates, and leads
- You create bar and line charts comparing to the previous week
- The reports are distributed to the sales team and executives
- This process connects to several other workflows, including the quarterly business review and sales team meetings

Would you like me to explain any part of this in more detail?"

**User:** "No, that's good. Can you show me all the tasks you've automated for me so far?"

**Lumora:** "I've successfully automated 4 recurring tasks for you:
1. Weekly Sales Report Generation (12 times, 95% success rate, 9 hours saved)
2. Invoice Processing for Acme Corp (23 times, 88% success rate, 12.3 hours saved)
3. Customer Support Ticket Categorization (156 times, 92% success rate, 20.8 hours saved)
4. Meeting Notes Distribution (18 times, 85% success rate, 7.5 hours saved)

In total, I've saved you approximately 49.6 hours over the past 3 months."

### Scene 4: New Automation Suggestion

**[User completes a task manually]**

**Lumora:** "I noticed you've performed this data analysis task 5 times in the past month, following a similar pattern each time. Would you like me to learn how to automate this for you?"

**User:** "What exactly did you observe?"

**Lumora:** "I observed that you:
1. Collect data from the marketing analytics platform
2. Clean the data by removing duplicates and formatting dates
3. Create pivot tables to analyze campaign performance
4. Generate visualizations of click-through rates and conversions
5. Export the results to a specific folder with a date-based filename

I'm 87% confident I can automate this entire workflow for you."

**User:** "Yes, please learn this task."

**Lumora:** "Great! Next time this task is needed, I'll notify you and can either run it automatically or with your supervision until you're comfortable with my execution."

<!-- ## Technical Implementation

This demo is powered by:
- **LangChain**: For orchestration and context management
- **LangGraph**: For agent workflow management
- **Neo4j**: For knowledge graph storage
- **Milvus**: For vector embeddings and semantic search
- **GraphRAG**: For enhanced retrieval combining vector search and graph traversal

## Key Capabilities Demonstrated

1. **Learning from User Behavior**: Lumora observes and learns from repetitive tasks
2. **Knowledge Graph Construction**: Automatic creation without manual intervention
3. **Task Automation**: Identification and automation of repetitive tasks
4. **Adaptive Learning**: Evolving knowledge representation as new information arrives
5. **User Collaboration**: Maintaining appropriate human oversight where needed -->