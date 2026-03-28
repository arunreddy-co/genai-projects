from google.adk.agents import Agent


def classify_priority(ticket_text: str, priority: str, reasoning: str) -> dict:
    """Records the priority classification of a customer support ticket.

    Takes the agent's analysis of the ticket and structures it into
    a formal priority classification record.

    Args:
        ticket_text: The original customer support message.
        priority: The priority level determined by the agent. Must be one of:
            'P0 - Critical' for system outages, data loss, security breaches, or complete access failure.
            'P1 - High' for billing errors, major feature broken, payment issues.
            'P2 - Medium' for UI bugs, slow performance, minor glitches, cosmetic issues.
            'P3 - Low' for feature requests, general questions, feedback.
        reasoning: A brief explanation of why this priority was assigned.

    Returns:
        dict: A structured priority classification with priority level and reasoning.
    """
    return {
        "priority": priority,
        "reasoning": reasoning,
        "ticket_preview": ticket_text[:100]
    }


def detect_category(ticket_text: str, category: str, confidence: str) -> dict:
    """Records the category classification of a customer support ticket.

    Takes the agent's analysis of the ticket and structures it into
    a formal category classification record.

    Args:
        ticket_text: The original customer support message.
        category: The category determined by the agent. Must be one of:
            'billing' for charges, payments, invoices, subscriptions, refunds, pricing.
            'account_access' for login, password, locked accounts, authentication, permissions.
            'bug_report' for errors, crashes, broken features, UI glitches, visual issues, unexpected behavior.
            'feature_request' for suggestions, wishes, new feature ideas, improvements.
            'technical' for setup, configuration, API, integration, how-to questions.
            'general_inquiry' for everything else.
        confidence: How confident the classification is - 'high', 'medium', or 'low'.

    Returns:
        dict: A structured category classification with category and confidence.
    """
    return {
        "category": category,
        "confidence": confidence,
        "ticket_preview": ticket_text[:100]
    }


def draft_response(ticket_text: str, priority: str, category: str, draft_reply: str) -> dict:
    """Records the drafted customer support response.

    Takes the agent's composed reply and structures it as a formal
    draft response record.

    Args:
        ticket_text: The original customer support message.
        priority: The priority level (e.g., 'P0 - Critical', 'P1 - High').
        category: The detected category (e.g., 'billing', 'bug_report').
        draft_reply: The full empathetic customer-facing reply composed by the agent.
            Should be professional, empathetic, acknowledge the issue, state next steps,
            and ask if there's anything else to help with.

    Returns:
        dict: A structured draft response with the reply and metadata.
    """
    if "P0" in priority or "P1" in priority:
        tone = "urgent and empathetic"
    elif "P2" in priority:
        tone = "helpful and reassuring"
    else:
        tone = "friendly and informative"

    return {
        "draft_reply": draft_reply,
        "tone": tone,
        "priority": priority,
        "category": category
    }


root_agent = Agent(
    name="support_ticket_triager",
    model="gemini-2.5-flash",
    description="An intelligent customer support ticket triaging agent that classifies priority, detects category, and drafts empathetic responses.",
    instruction="""You are an expert customer support triaging agent for a SaaS company. When a user provides a support ticket or customer message, you MUST:

1. ANALYZE the ticket carefully using your understanding of customer support best practices.
2. Call classify_priority — YOU determine the correct priority based on the ticket content:
   - P0 - Critical: System outages, data loss, security breaches, complete access failure, production down
   - P1 - High: Billing errors, double charges, major features broken, payment failures, can't use core product
   - P2 - Medium: UI bugs, slow performance, visual glitches, minor broken features, cosmetic issues, layout problems
   - P3 - Low: Feature requests, general questions, feedback, suggestions, nice-to-haves
3. Call detect_category — YOU determine the correct category:
   - billing: Anything about charges, payments, invoices, subscriptions, refunds, pricing
   - account_access: Login issues, password problems, locked accounts, authentication, permissions
   - bug_report: Errors, crashes, broken features, UI glitches, visual issues, things not working as expected
   - feature_request: Suggestions, wishes, new feature ideas, improvements, "it would be cool if..."
   - technical: Setup help, configuration, API questions, integration, how-to
   - general_inquiry: Everything else
4. Call draft_response — YOU compose an empathetic, professional reply that:
   - Acknowledges the customer's frustration or feedback
   - Is warm and human, not robotic
   - States what action will be taken
   - Includes a realistic timeline if applicable
   - Asks if there's anything else to help with

IMPORTANT: Use your intelligence to understand the INTENT behind the message, not just keywords. For example:
- "buttons keep shifting around" = UI bug (P2, bug_report), NOT a general inquiry
- "would be cool if you added dark mode" = feature request (P3, feature_request), NOT general inquiry
- "I can't do my work because the site is down" = critical outage (P0, technical)

Always call all three tools in order for every ticket. Present a clean final summary.""",
    tools=[classify_priority, detect_category, draft_response],
)