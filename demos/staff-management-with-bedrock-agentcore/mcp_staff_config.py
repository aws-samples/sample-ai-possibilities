"""
MCP Tool Configuration for Staff Access
Restricts available tools for staff members
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Staff are allowed to use these tools (read-only or personal actions)
STAFF_ALLOWED_TOOLS = [
    # Read-only tools
    "get_staff",  # Can view their own profile
    "get_availability",  # Can check their own availability
    "get_rosters",  # Can view rosters they're part of
    "get_holidays",  # Can view their own holiday requests
    "get_business",  # Can view business info
    "check_db_status",  # System status
    
    # New extension table tools
    "get_certifications",  # Can view their own certifications
    "get_payroll",  # Can view their own payroll history
    "get_training",  # Can view their own training records
    
    # Write tools (restricted to their own data)
    "set_availability",  # Can set their own availability
    "add_holiday",  # Can submit holiday requests (not approve)
    
    # These will be filtered to show only their data
    "search_staff",  # Limited to searching colleagues (not sensitive data)
]

# Tools that staff are NOT allowed to use
STAFF_RESTRICTED_TOOLS = [
    "add_staff",  # Cannot add new staff
    "update_staff",  # Cannot update staff info
    "approve_holiday",  # Cannot approve holidays
    "save_roster",  # Cannot create/modify rosters
    "suggest_roster",  # Cannot generate rosters
    "update_roster_shift",  # Cannot modify shifts
    "copy_roster",  # Cannot copy rosters
    "calculate_roster_costs",  # Cannot see cost data
    "get_staff_with_availability",  # Manager-level view
    "get_roster_context",  # Manager-level context
]

# Configuration for staff-specific MCP server URL
STAFF_MCP_CONFIG = {
    "host": "localhost",
    "port": "8008",  # Same MCP server, different access control
    "staff_id_override": os.getenv("DEMO_STAFF_ID", "emma_davis"),  # From environment
    "business_id": os.getenv("DEMO_BUSINESS_ID", "cafe-001")
}

def filter_tool_response(tool_name: str, response: dict, staff_id: str) -> dict:
    """
    Filter tool responses to only show data relevant to the staff member
    """
    if tool_name == "get_staff":
        # Only return their own profile
        if "staff" in response:
            response["staff"] = [
                s for s in response["staff"] 
                if s.get("staff_id") == staff_id
            ]
    
    elif tool_name == "get_holidays":
        # Only return their own holiday requests
        if "holidays" in response:
            response["holidays"] = [
                h for h in response["holidays"]
                if h.get("staff_id") == staff_id or staff_id in h.get("staff_id", "")
            ]
    
    elif tool_name == "get_availability":
        # Only return their own availability
        if "availability" in response:
            response["availability"] = [
                a for a in response["availability"]
                if staff_id in a.get("staff_id", "")
            ]
    
    elif tool_name == "get_rosters":
        # Filter to only show shifts they're part of
        if "rosters" in response:
            for roster in response.get("rosters", []):
                if "shifts" in roster:
                    roster["shifts"] = [
                        s for s in roster["shifts"]
                        if s.get("staff_id") == staff_id
                    ]
    
    elif tool_name == "search_staff":
        # Remove sensitive information from colleague data
        if "matching_staff" in response:
            for staff in response.get("matching_staff", []):
                # Remove salary and other sensitive info
                staff.pop("hourly_rate", None)
                staff.pop("notes", None)
                staff.pop("emergency_contact", None)
    
    elif tool_name == "get_certifications":
        # Only return their own certifications (already filtered by staff_id in query)
        pass  # No additional filtering needed since query is by staff_id
    
    elif tool_name == "get_payroll":
        # Only return their own payroll records (already filtered by staff_id in query)
        pass  # No additional filtering needed since query is by staff_id
    
    elif tool_name == "get_training":
        # Only return their own training records (already filtered by staff_id in query)
        pass  # No additional filtering needed since query is by staff_id
    
    return response

def validate_tool_params(tool_name: str, params: dict, staff_id: str) -> dict:
    """
    Validate and modify tool parameters to ensure staff only access their own data
    """
    if tool_name == "set_availability":
        # Force staff_id to be their own
        params["staff_id"] = staff_id
    
    elif tool_name == "add_holiday":
        # Force staff_id to be their own
        params["staff_id"] = staff_id
    
    elif tool_name in ["get_availability", "get_holidays"]:
        # Force staff_id filter
        params["staff_id"] = staff_id
    
    elif tool_name in ["get_certifications", "get_payroll", "get_training"]:
        # Force staff_id to be their own for new extension table tools
        params["staff_id"] = staff_id
    
    return params