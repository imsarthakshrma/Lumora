import random
from datetime import datetime, timedelta
import json
import os

# mock user tasks that Lumora could learn to automate
TASK_TYPES = [
    "email_response",
    "data_entry",
    "report_generation",
    "calendar_scheduling",
    "document_filing",
    "invoice_processing",
    "customer_support_ticket",
    "data_analysis",
    "social_media_posting",
    "meeting_notes"
]

# mock task attributes
PRIORITIES = ["high", "medium", "low"]
STATUSES = ["pending", "in_progress", "completed", "automated"]
FREQUENCY = ["daily", "weekly", "monthly", "quarterly", "ad_hoc"]
DEPARTMENTS = ["marketing", "sales", "finance", "hr", "engineering", "customer_support"]

# mock task steps for different task types
TASK_STEPS = {
    "email_response": [
        "open_email_client", "read_message", "categorize_email", "draft_response", "review_response", "send_response"
    ],
    "data_entry": [
        "open_data_source", "extract_data", "validate_data", "format_data", "enter_data", "verify_entry"
    ],
    "report_generation": [
        "gather_data", "analyze_data", "create_charts", "write_summary", "format_report", "distribute_report"
    ],
    "calendar_scheduling": [
        "check_availability", "select_time_slot", "create_event", "add_participants", "set_reminders", "send_invites"
    ],
    "document_filing": [
        "receive_document", "categorize_document", "name_file", "select_storage_location", "save_document", "update_index"
    ],
    "invoice_processing": [
        "receive_invoice", "verify_details", "match_with_purchase_order", "approve_payment", "record_transaction", "archive_invoice"
    ],
    "customer_support_ticket": [
        "receive_ticket", "categorize_issue", "research_solution", "draft_response", "resolve_ticket", "follow_up"
    ],
    "data_analysis": [
        "collect_data", "clean_data", "analyze_trends", "create_visualizations", "interpret_results", "prepare_findings"
    ],
    "social_media_posting": [
        "plan_content", "create_media", "write_caption", "select_hashtags", "schedule_post", "monitor_engagement"
    ],
    "meeting_notes": [
        "prepare_template", "record_key_points", "note_action_items", "organize_notes", "distribute_to_participants", "follow_up_on_actions"
    ]
}

# entities that might appear in tasks (for knowledge graph construction)
ENTITIES = {
    "people": ["John Smith", "Maria Garcia", "Wei Chen", "Aisha Patel", "Robert Johnson", "Emma Williams"],
    "tools": ["Outlook", "Excel", "Salesforce", "Jira", "Slack", "Google Docs", "Asana", "Tableau", "Zoom", "QuickBooks"],
    "documents": ["Invoice", "Report", "Presentation", "Contract", "Proposal", "Specification", "Manual"],
    "systems": ["CRM", "ERP", "HRIS", "CMS", "Accounting System", "Project Management Tool", "Ticketing System"]
}

# define learned automation patterns (what Lumora has already learned)
LEARNED_AUTOMATIONS = [
    {
        "automation_id": 1,
        "name": "Weekly Sales Report Generation",
        "task_type": "report_generation",
        "trigger_condition": "Every Monday at 9:00 AM",
        "steps": [
            {"action": "gather_data", "parameters": {"source": "Salesforce", "report_type": "weekly_sales"}},
            {"action": "analyze_data", "parameters": {"metrics": ["revenue", "conversion_rate", "leads"]}},
            {"action": "create_charts", "parameters": {"chart_types": ["bar", "line"], "comparison": "previous_week"}},
            {"action": "format_report", "parameters": {"template": "sales_weekly", "branding": True}},
            {"action": "distribute_report", "parameters": {"recipients": ["sales_team", "executives"], "format": "pdf"}}
        ],
        "success_rate": 0.95,
        "times_executed": 12,
        "last_executed": (datetime.now() - timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d"),
        "average_time_saved": 45  # minutes
    },
    {
        "automation_id": 2,
        "name": "Invoice Processing for Acme Corp",
        "task_type": "invoice_processing",
        "trigger_condition": "Email received from accounting@acmecorp.com",
        "steps": [
            {"action": "receive_invoice", "parameters": {"source": "email", "filter": "from:accounting@acmecorp.com"}},
            {"action": "verify_details", "parameters": {"required_fields": ["invoice_number", "amount", "due_date"]}},
            {"action": "match_with_purchase_order", "parameters": {"po_system": "ERP", "match_fields": ["po_number"]}},
            {"action": "approve_payment", "parameters": {"approval_workflow": "standard", "threshold": 5000}},
            {"action": "record_transaction", "parameters": {"system": "QuickBooks", "category": "vendor_payment"}},
            {"action": "archive_invoice", "parameters": {"location": "finance_archive", "retention": "7_years"}}
        ],
        "success_rate": 0.88,
        "times_executed": 23,
        "last_executed": (datetime.now() - timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d"),
        "average_time_saved": 32  # minutes
    },
    {
        "automation_id": 3,
        "name": "Customer Support Ticket Categorization",
        "task_type": "customer_support_ticket",
        "trigger_condition": "New ticket created in support system",
        "steps": [
            {"action": "receive_ticket", "parameters": {"source": "support_portal"}},
            {"action": "categorize_issue", "parameters": {"categories": ["technical", "billing", "feature_request", "bug"]}},
            {"action": "assign_priority", "parameters": {"rules": ["keywords", "customer_tier", "issue_type"]}},
            {"action": "route_to_team", "parameters": {"teams": ["technical_support", "billing", "product_management"]}}
        ],
        "success_rate": 0.92,
        "times_executed": 156,
        "last_executed": (datetime.now() - timedelta(hours=random.randint(1, 24))).strftime("%Y-%m-%d %H:%M:%S"),
        "average_time_saved": 8  # minutes
    },
    {
        "automation_id": 4,
        "name": "Meeting Notes Distribution",
        "task_type": "meeting_notes",
        "trigger_condition": "Calendar event with 'Team Meeting' in title ends",
        "steps": [
            {"action": "prepare_template", "parameters": {"template": "team_meeting_notes"}},
            {"action": "extract_key_points", "parameters": {"from": "meeting_recording", "topics": ["decisions", "action_items"]}},
            {"action": "organize_notes", "parameters": {"format": "bullet_points", "sections": ["summary", "decisions", "action_items"]}},
            {"action": "distribute_to_participants", "parameters": {"method": "email", "include_recording": True}}
        ],
        "success_rate": 0.85,
        "times_executed": 18,
        "last_executed": (datetime.now() - timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d"),
        "average_time_saved": 25  # minutes
    }
]

# user preferences that Lumora has learned
USER_PREFERENCES = {
    "communication": {
        "preferred_channel": "slack",
        "notification_frequency": "daily_digest",
        "working_hours": "9:00-17:00",
        "do_not_disturb": ["12:00-13:00", "during_calendar_meetings"]
    },
    "task_priorities": {
        "email_response": "medium",
        "customer_support_ticket": "high",
        "report_generation": "high",
        "data_entry": "low"
    },
    "automation_preferences": {
        "require_confirmation": ["invoice_processing", "email_response"],
        "fully_automated": ["data_entry", "document_filing", "meeting_notes"],
        "never_automate": []
    },
    "tool_preferences": {
        "email": "Outlook",
        "documents": "Google Docs",
        "project_management": "Asana",
        "communication": "Slack"
    }
}

def generate_mock_task(task_id, include_automation_status=True):
    """Generate a single mock task with realistic attributes"""
    task_type = random.choice(TASK_TYPES)
    
    # create date within last 30 days
    days_ago = random.randint(0, 30)
    created_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    
    # generate steps performed based on task type
    steps_performed = []
    if random.random() > 0.3:  # 70% of tasks have recorded steps
        available_steps = TASK_STEPS.get(task_type, ["generic_step_1", "generic_step_2", "generic_step_3"])
        num_steps = min(len(available_steps), random.randint(2, len(available_steps)))
        selected_steps = available_steps[:num_steps]  # take steps in order
        
        for i, step_name in enumerate(selected_steps):
            steps_performed.append({
                "step_id": i+1,
                "action": step_name,
                "timestamp": (datetime.now() - timedelta(days=days_ago, 
                                                        hours=random.randint(0, 23),
                                                        minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S"),
                "result": random.choice(["success", "partial", "failed"]) if random.random() > 0.8 else "success"
            })
    
    # Add relevant entities to the task
    task_entities = {
        "people": random.sample(ENTITIES["people"], random.randint(0, 2)),
        "tools": random.sample(ENTITIES["tools"], random.randint(1, 3)),
        "documents": random.sample(ENTITIES["documents"], random.randint(0, 2)) if random.random() > 0.5 else [],
        "systems": random.sample(ENTITIES["systems"], random.randint(0, 2)) if random.random() > 0.5 else []
    }
    
    # determine if this task was automated
    was_automated = random.random() > 0.7 if include_automation_status else False
    status = "automated" if was_automated else random.choice(["pending", "in_progress", "completed"])
    
    # if automated, link to one of the learned automations
    automation_info = None
    if was_automated and LEARNED_AUTOMATIONS:
        matching_automations = [a for a in LEARNED_AUTOMATIONS if a["task_type"] == task_type]
        if matching_automations:
            selected_automation = random.choice(matching_automations)
            automation_info = {
                "automation_id": selected_automation["automation_id"],
                "name": selected_automation["name"],
                "execution_time": (datetime.now() - timedelta(days=days_ago-1, 
                                                            hours=random.randint(0, 12))).strftime("%Y-%m-%d %H:%M:%S"),
                "success": random.random() < selected_automation["success_rate"],
                "time_saved": selected_automation["average_time_saved"] * (0.8 + random.random() * 0.4)  # +/- 20%
            }
    
    # generate task metadata
    task = {
        "task_id": task_id,
        "task_type": task_type,
        "title": f"{task_type.replace('_', ' ').title()} Task {task_id}",
        "description": f"This is a {task_type.replace('_', ' ')} task that requires processing {random.choice(task_entities['documents'] if task_entities['documents'] else ['data'])} using {', '.join(task_entities['tools'][:1])}.",
        "created_date": created_date,
        "priority": USER_PREFERENCES["task_priorities"].get(task_type, random.choice(PRIORITIES)),
        "status": status,
        "frequency": random.choice(FREQUENCY),
        "department": random.choice(DEPARTMENTS),
        "steps_performed": steps_performed,
        "time_spent_minutes": 0 if was_automated else random.randint(5, 120),
        "automation_candidate": True if was_automated else random.random() > 0.5,
        "entities": task_entities,
        "metadata": {
            "source_system": random.choice(["email", "slack", "jira", "salesforce", "internal_tool"]),
            "complexity": random.choice(["simple", "moderate", "complex"]),
            "dependencies": random.sample(TASK_TYPES, random.randint(0, 3)) if random.random() > 0.7 else []
        }
    }
    
    # add automation info if the task was automated
    if automation_info:
        task["automation"] = automation_info
    
    return task

def generate_task_patterns():
    """Generate patterns of tasks that are frequently performed together"""
    patterns = []
    
    # create 3-5 common patterns
    num_patterns = random.randint(3, 5)
    for i in range(num_patterns):
        pattern_tasks = random.sample(TASK_TYPES, random.randint(2, 4))
        patterns.append({
            "pattern_id": i+1,
            "name": f"Common Pattern {i+1}",
            "tasks": pattern_tasks,
            "frequency": random.choice(FREQUENCY),
            "typical_sequence": True if random.random() > 0.3 else False,
            "automation_potential": random.randint(1, 10) / 10,  # Score between 0.1 and 1.0
            "confidence": random.randint(70, 95) / 100  # Confidence in this pattern
        })
    
    return patterns

def generate_mock_dataset(num_tasks=50):
    """Generate a set of mock tasks"""
    tasks = []
    for i in range(1, num_tasks+1):
        tasks.append(generate_mock_task(i))
    
    # generate task patterns
    patterns = generate_task_patterns()
    
    # create a dataset that represents what Lumora has already learned
    dataset = {
        "tasks": tasks,
        "patterns": patterns,
        "learned_automations": LEARNED_AUTOMATIONS,
        "user_preferences": USER_PREFERENCES,
        "learning_statistics": {
            "total_tasks_observed": num_tasks + random.randint(100, 500),
            "total_tasks_automated": sum(1 for task in tasks if task.get("status") == "automated"),
            "total_time_saved_minutes": sum(a["average_time_saved"] * a["times_executed"] for a in LEARNED_AUTOMATIONS),
            "automation_success_rate": sum(a["success_rate"] * a["times_executed"] for a in LEARNED_AUTOMATIONS) / 
                                      sum(a["times_executed"] for a in LEARNED_AUTOMATIONS),
            "learning_period_days": 90
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return dataset

def save_mock_data(filename="mock_tasks.json", num_tasks=50):
    """Generate and save mock data to a JSON file"""
    data = generate_mock_dataset(num_tasks)
    
    # create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {num_tasks} mock tasks and saved to {filename}")
    return data

if __name__ == "__main__":
    save_mock_data("../data/mock_tasks.json", 50)