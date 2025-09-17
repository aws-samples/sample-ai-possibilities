import os
import boto3
from mcp.server import FastMCP
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
import json
from dotenv import load_dotenv
from boto3.dynamodb.conditions import Key, Attr

# Load environment variables
load_dotenv()

# Get MCP server configuration from environment
MCP_HOST = os.getenv("MCP_HOST", "localhost")
MCP_PORT = os.getenv("MCP_PORT", "8008")

# Set the correct environment variables that FastMCP actually reads
os.environ["FASTMCP_PORT"] = MCP_PORT
os.environ["FASTMCP_HOST"] = MCP_HOST

mcp = FastMCP("StaffCast DynamoDB", port = MCP_PORT)

# DynamoDB configuration
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
STAFF_TABLE = os.getenv("STAFF_TABLE_NAME", "staffcast-staff")
ROSTER_TABLE = os.getenv("ROSTER_TABLE_NAME", "staffcast-rosters")
AVAILABILITY_TABLE = os.getenv("AVAILABILITY_TABLE_NAME", "staffcast-availability")
BUSINESS_TABLE = os.getenv("BUSINESS_TABLE_NAME", "staffcast-businesses")
HOLIDAYS_TABLE = os.getenv("HOLIDAYS_TABLE_NAME", "staffcast-holidays")

# New extension tables
CERTIFICATIONS_TABLE = os.getenv("CERTIFICATIONS_TABLE_NAME", "staffcast-certifications")
PAYROLL_TABLE = os.getenv("PAYROLL_TABLE_NAME", "staffcast-payroll")
TRAINING_TABLE = os.getenv("TRAINING_TABLE_NAME", "staffcast-training")

# Initialize DynamoDB (AWS only)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj

@mcp.tool(description="List all DynamoDB tables")
def list_tables() -> Dict[str, Any]:
    """
    List all available DynamoDB tables for StaffCast.
    
    Returns:
        Dictionary with list of tables and their status
    """
    try:
        tables = []
        expected_tables = {
            STAFF_TABLE: "Staff members",
            ROSTER_TABLE: "Work rosters",
            AVAILABILITY_TABLE: "Staff availability",
            BUSINESS_TABLE: "Business configurations",
            HOLIDAYS_TABLE: "Staff holidays"
        }
        
        existing_tables = list(dynamodb.tables.all())
        existing_table_names = [table.name for table in existing_tables]
        
        for table_name, description in expected_tables.items():
            status = "exists" if table_name in existing_table_names else "not found"
            tables.append({
                "table_name": table_name,
                "description": description,
                "status": status
            })
        
        return {
            "success": True,
            "tables": tables,
            "total": len(tables)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tables": []
        }

@mcp.tool(description="Get all staff members")
def get_staff(business_id: str, position: Optional[str] = None, active_only: bool = True) -> Dict[str, Any]:
    """
    Retrieve staff members for a business.
    
    Args:
        business_id: The business identifier
        position: Optional filter by position
        active_only: Whether to return only active staff (default: True)
    
    Returns:
        Dictionary with staff members
    """
    try:
        table = dynamodb.Table(STAFF_TABLE)
        
        # Query by business_id
        response = table.query(
            KeyConditionExpression=Key('business_id').eq(business_id)
        )
        
        staff = response.get('Items', [])
        
        # Apply filters
        if position:
            staff = [s for s in staff if s.get('position') == position]
        
        if active_only:
            staff = [s for s in staff if s.get('is_active', 'true') == 'true']
        
        # Calculate additional info for each staff member
        for member in staff:
            # Calculate tenure if hire_date exists
            if 'hire_date' in member:
                hire_date = datetime.fromisoformat(member['hire_date'].replace('Z', '+00:00'))
                tenure_days = (datetime.utcnow() - hire_date).days
                member['tenure_days'] = tenure_days
                member['tenure_text'] = f"{tenure_days // 365} years, {(tenure_days % 365) // 30} months"
        
        # Convert Decimal to float for JSON serialization
        staff = decimal_to_float(staff)
        
        return {
            "success": True,
            "business_id": business_id,
            "count": len(staff),
            "staff": staff
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "staff": []
        }

@mcp.tool(description="Add a new staff member")
def add_staff(
    business_id: str,
    staff_id: str,
    name: str,
    position: str,
    email: str,
    phone: str,
    experience_level: str = "junior",
    hourly_rate: float = 25.0,
    skills: Optional[List[str]] = None,
    preferred_hours: Optional[int] = 40,
    shifts_available: Optional[List[str]] = None,
    hire_date: Optional[str] = None,
    emergency_contact: Optional[Dict[str, str]] = None,
    certifications: Optional[List[Dict[str, str]]] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new staff member to the system.
    
    Args:
        business_id: The business identifier
        staff_id: Unique staff identifier
        name: Full name of the staff member
        position: Job position (e.g., "barista", "manager", "chef")
        email: Email address
        phone: Phone number
        experience_level: "junior", "intermediate", "senior"
        hourly_rate: Hourly pay rate
        skills: List of skills
        preferred_hours: Preferred hours per week
        shifts_available: List of shift preferences ["morning", "afternoon", "evening", "night", "weekend"]
        hire_date: When the staff member was hired (YYYY-MM-DD)
        emergency_contact: {"name": "string", "phone": "string", "relationship": "string"}
        certifications: List of certifications [{"name": "string", "expiry_date": "YYYY-MM-DD"}]
        notes: Additional notes
    
    Returns:
        Dictionary with operation result
    """
    try:
        table = dynamodb.Table(STAFF_TABLE)
        
        item = {
            'business_id': business_id,
            'staff_id': staff_id,
            'name': name,
            'position': position,
            'email': email,
            'phone': phone,
            'experience_level': experience_level,
            'hourly_rate': Decimal(str(hourly_rate)),
            'skills': skills or [],
            'preferred_hours': preferred_hours,
            'shifts_available': shifts_available or ["morning", "afternoon", "evening"],
            'is_active': 'true',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'hire_date': hire_date or datetime.utcnow().isoformat()
        }
        
        if emergency_contact:
            item['emergency_contact'] = emergency_contact
            
        if certifications:
            item['certifications'] = certifications
            
        if notes:
            item['notes'] = notes
        
        table.put_item(Item=item)
        
        return {
            "success": True,
            "message": f"Staff member {name} added successfully",
            "staff": decimal_to_float(item)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Get staff holidays")
def get_holidays(
    business_id: str,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get staff holiday requests and approved holidays.
    
    Args:
        business_id: The business identifier
        staff_id: Optional specific staff member
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        status: Optional status filter ("pending", "approved", "rejected")
    
    Returns:
        Dictionary with holiday data
    """
    try:
        table = dynamodb.Table(HOLIDAYS_TABLE)
        
        if staff_id:
            # Query for specific staff member
            response = table.query(
                KeyConditionExpression=Key('staff_id').eq(f"{business_id}#{staff_id}")
            )
        else:
            # Scan for all staff in business
            response = table.scan(
                FilterExpression=Attr('business_id').eq(business_id)
            )
        
        holidays = response.get('Items', [])
        
        # Apply filters
        if start_date and end_date:
            holidays = [
                h for h in holidays
                if h.get('start_date') <= end_date and h.get('end_date') >= start_date
            ]
        
        if status:
            holidays = [h for h in holidays if h.get('status') == status]
        
        holidays = decimal_to_float(holidays)
        
        return {
            "success": True,
            "business_id": business_id,
            "count": len(holidays),
            "holidays": holidays
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "holidays": []
        }

@mcp.tool(description="Add a holiday request")
def add_holiday(
    business_id: str,
    staff_id: str,
    start_date: str,
    end_date: str,
    type: str = "annual_leave",
    reason: Optional[str] = None,
    status: str = "pending"
) -> Dict[str, Any]:
    """
    Add a holiday request for a staff member.
    
    Args:
        business_id: The business identifier
        staff_id: Staff member ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        type: Holiday type ("annual_leave", "sick_leave", "personal_leave", "unpaid_leave")
        reason: Optional reason for the leave
        status: Status ("pending", "approved", "rejected")
    
    Returns:
        Dictionary with operation result
    """
    try:
        table = dynamodb.Table(HOLIDAYS_TABLE)
        
        # Calculate number of days
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days + 1
        
        item = {
            'staff_id': f"{business_id}#{staff_id}",
            'holiday_id': f"HOL{datetime.utcnow().timestamp():.0f}",
            'business_id': business_id,
            'start_date': start_date,
            'end_date': end_date,
            'days': days,
            'type': type,
            'status': status,
            'requested_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if reason:
            item['reason'] = reason
        
        table.put_item(Item=item)
        
        return {
            "success": True,
            "message": f"Holiday request added for {staff_id}",
            "holiday": decimal_to_float(item)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Get staff availability for a date range")
def get_availability(
    business_id: str,
    start_date: str,
    end_date: str,
    staff_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get staff availability for a given date range.
    
    Args:
        business_id: The business identifier
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        staff_id: Optional specific staff member
    
    Returns:
        Dictionary with availability data
    """
    try:
        table = dynamodb.Table(AVAILABILITY_TABLE)
        
        if staff_id:
            # Query for specific staff member
            response = table.query(
                KeyConditionExpression=Key('staff_id').eq(f"{business_id}#{staff_id}") & 
                                     Key('date').between(start_date, end_date)
            )
        else:
            # Scan for all staff in date range (less efficient)
            response = table.scan(
                FilterExpression=Attr('business_id').eq(business_id) & 
                               Attr('date').between(start_date, end_date)
            )
        
        availability = response.get('Items', [])
        
        # Check for holidays that affect availability
        holidays = get_holidays(business_id, staff_id, start_date, end_date, "approved")
        holiday_dates = set()
        
        for holiday in holidays.get('holidays', []):
            h_start = datetime.strptime(holiday['start_date'], '%Y-%m-%d')
            h_end = datetime.strptime(holiday['end_date'], '%Y-%m-%d')
            current = h_start
            while current <= h_end:
                holiday_dates.add(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        
        # Mark holiday dates in availability
        for avail in availability:
            if avail['date'] in holiday_dates:
                avail['on_holiday'] = True
                avail['available'] = 'false'  # String format for consistency
        
        availability = decimal_to_float(availability)
        
        return {
            "success": True,
            "business_id": business_id,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(availability),
            "availability": availability,
            "holiday_dates": list(holiday_dates)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "availability": []
        }

@mcp.tool(description="Set staff availability")
def set_availability(
    business_id: str,
    staff_id: str,
    date: str,
    available: bool,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Set staff availability for a specific date.
    
    Args:
        business_id: The business identifier
        staff_id: Staff member ID
        date: Date (YYYY-MM-DD)
        available: Whether staff is available
        start_time: Available from time (HH:MM)
        end_time: Available until time (HH:MM)
        notes: Optional notes
    
    Returns:
        Dictionary with operation result
    """
    try:
        table = dynamodb.Table(AVAILABILITY_TABLE)
        
        item = {
            'staff_id': f"{business_id}#{staff_id}",
            'date': date,
            'business_id': business_id,
            'available': 'true' if available else 'false',  # String for GSI compatibility
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if available and start_time and end_time:
            item['start_time'] = start_time
            item['end_time'] = end_time
        
        if notes:
            item['notes'] = notes
        
        table.put_item(Item=item)
        
        return {
            "success": True,
            "message": f"Availability updated for {staff_id} on {date}",
            "availability": decimal_to_float(item)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Get rosters for a date range")
def get_rosters(
    business_id: str,
    start_date: str,
    end_date: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get rosters for a business within a date range.
    
    Args:
        business_id: The business identifier
        start_date: Start date (YYYY-MM-DD)
        end_date: Optional end date (defaults to start_date)
        status: Optional filter by status ("draft", "published", "archived")
    
    Returns:
        Dictionary with roster data
    """
    try:
        table = dynamodb.Table(ROSTER_TABLE)
        
        if not end_date:
            end_date = start_date
        
        response = table.query(
            KeyConditionExpression=Key('business_id').eq(business_id) & 
                                 Key('roster_date').between(start_date, end_date)
        )
        
        rosters = response.get('Items', [])
        
        if status:
            rosters = [r for r in rosters if r.get('status') == status]
        
        rosters = decimal_to_float(rosters)
        
        return {
            "success": True,
            "business_id": business_id,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(rosters),
            "rosters": rosters
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rosters": []
        }

@mcp.tool(description="Create or update a roster")
def save_roster(
    business_id: str,
    roster_date: str,
    shifts: List[Dict[str, Any]],
    status: str = "draft",
    notes: Optional[str] = None,
    weather_forecast: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create or update a roster for a specific date.
    
    Args:
        business_id: The business identifier
        roster_date: Date of the roster (YYYY-MM-DD)
        shifts: List of shift assignments
        status: "draft", "published", or "archived"
        notes: Optional notes
        weather_forecast: Optional weather data that influenced the roster
    
    Shift format:
        {
            "staff_id": "string",
            "start_time": "HH:MM",
            "end_time": "HH:MM",
            "position": "string",
            "break_duration": 30  # minutes
        }
    
    Returns:
        Dictionary with operation result
    """
    try:
        table = dynamodb.Table(ROSTER_TABLE)
        
        # Calculate total hours and labor cost
        total_hours = 0
        total_cost = 0
        
        # Enrich shifts with staff data
        staff_table = dynamodb.Table(STAFF_TABLE)
        for shift in shifts:
            # Get staff member details
            staff_response = staff_table.get_item(
                Key={
                    'business_id': business_id,
                    'staff_id': shift['staff_id']
                }
            )
            
            if 'Item' in staff_response:
                staff = staff_response['Item']
                shift['staff_name'] = staff['name']
                shift['name'] = staff['name']  # Add 'name' field for compatibility
                hourly_rate = float(staff.get('hourly_rate', 0))
                shift['hourly_rate'] = Decimal(str(hourly_rate))
                
                # Calculate hours
                start = datetime.strptime(shift['start_time'], '%H:%M')
                end = datetime.strptime(shift['end_time'], '%H:%M')
                hours = (end - start).total_seconds() / 3600
                hours -= shift.get('break_duration', 30) / 60  # Subtract break
                
                shift['hours'] = Decimal(str(hours))
                shift_cost = hours * hourly_rate
                shift['shift_cost'] = Decimal(str(shift_cost))
                
                total_hours += hours
                total_cost += shift_cost
        
        item = {
            'business_id': business_id,
            'roster_date': roster_date,
            'shifts': shifts,
            'status': status,
            'total_hours': Decimal(str(total_hours)),
            'total_cost': Decimal(str(total_cost)),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if notes:
            item['notes'] = notes
            
        if weather_forecast:
            item['weather_forecast'] = weather_forecast
        
        table.put_item(Item=item)
        
        return {
            "success": True,
            "message": f"Roster saved for {roster_date}",
            "roster": decimal_to_float(item)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Generate roster suggestions based on parameters")
def suggest_roster(
    business_id: str,
    roster_date: str,
    expected_customers: Optional[int] = None,
    weather_conditions: Optional[str] = None,
    special_events: Optional[List[str]] = None,
    min_staff: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Generate roster suggestions based on various parameters.
    
    Args:
        business_id: The business identifier
        roster_date: Date for the roster (YYYY-MM-DD)
        expected_customers: Expected number of customers
        weather_conditions: "sunny", "rainy", "stormy", etc.
        special_events: List of special events
        min_staff: Minimum staff requirements by position
    
    Returns:
        Dictionary with roster suggestions
    """
    try:
        # Get available staff
        availability_data = get_availability(business_id, roster_date, roster_date)
        available_staff = availability_data.get('availability', [])
        
        # Get all staff members
        staff_data = get_staff(business_id)
        all_staff = {s['staff_id']: s for s in staff_data.get('staff', [])}
        
        # Filter to only available staff (not on holiday)
        available_staff_ids = {
            a['staff_id'].split('#')[1] 
            for a in available_staff 
            if a.get('available') and not a.get('on_holiday', False)
        }
        available_staff_details = [all_staff[sid] for sid in available_staff_ids if sid in all_staff]
        
        # Default minimum staff requirements
        if not min_staff:
            min_staff = {
                "manager": 1,
                "barista": 2,
                "chef": 1
            }
        
        # Adjust based on parameters
        if expected_customers and expected_customers > 200:
            min_staff["barista"] = 3
            min_staff["chef"] = 2
        
        if weather_conditions in ["sunny", "warm"]:
            min_staff["barista"] = max(min_staff.get("barista", 2), 3)
        
        if special_events:
            for position in min_staff:
                min_staff[position] = int(min_staff[position] * 1.5)
        
        # Build roster suggestions
        suggested_shifts = []
        positions_filled = {pos: 0 for pos in min_staff}
        
        # Sort staff by experience level (senior first) and tenure
        experience_order = {"senior": 1, "intermediate": 2, "junior": 3}
        available_staff_details.sort(
            key=lambda x: (
                experience_order.get(x.get('experience_level', 'junior'), 4),
                -x.get('tenure_days', 0),
                x.get('name')
            )
        )
        
        # Assign shifts based on requirements and staff preferences
        for staff in available_staff_details:
            position = staff.get('position')
            if position in positions_filled and positions_filled[position] < min_staff.get(position, 0):
                # Get staff's available times for this date
                staff_avail = next(
                    (a for a in available_staff if f"#{staff['staff_id']}" in a.get('staff_id', '')),
                    {}
                )
                
                # Check staff's shift preferences
                shifts_available = staff.get('shifts_available', ["morning", "afternoon", "evening"])
                
                # Standard shift times based on position and preferences
                if "morning" in shifts_available and positions_filled[position] == 0:
                    shift_times = {
                        "manager": ("08:00", "16:00"),
                        "barista": ("06:00", "14:00"),
                        "chef": ("06:00", "14:00")
                    }
                elif "afternoon" in shifts_available:
                    shift_times = {
                        "manager": ("12:00", "20:00"),
                        "barista": ("11:00", "19:00"),
                        "chef": ("12:00", "20:00")
                    }
                else:  # evening
                    shift_times = {
                        "manager": ("14:00", "22:00"),
                        "barista": ("14:00", "22:00"),
                        "chef": ("14:00", "22:00")
                    }
                
                start, end = shift_times.get(position, ("09:00", "17:00"))
                
                # Use staff's specific availability if provided
                if staff_avail.get('start_time') and staff_avail.get('end_time'):
                    start = staff_avail['start_time']
                    end = staff_avail['end_time']
                
                suggested_shifts.append({
                    "staff_id": staff['staff_id'],
                    "staff_name": staff['name'],
                    "name": staff['name'],  # Include both for compatibility
                    "position": position,
                    "start_time": start,
                    "end_time": end,
                    "break_duration": 30,
                    "experience_level": staff.get('experience_level', 'junior'),
                    "tenure_text": staff.get('tenure_text', 'New'),
                    "hourly_rate": staff.get('hourly_rate', 0)  # Include rate for cost calculation
                })
                
                positions_filled[position] += 1
        
        # Generate reasoning
        reasoning = []
        if weather_conditions:
            reasoning.append(f"Weather forecast: {weather_conditions}")
        if expected_customers:
            reasoning.append(f"Expected customers: {expected_customers}")
        if special_events:
            reasoning.append(f"Special events: {', '.join(special_events)}")
        
        for pos, count in positions_filled.items():
            if count < min_staff.get(pos, 0):
                reasoning.append(f"Warning: Only {count}/{min_staff[pos]} {pos}s available")
        
        if availability_data.get('holiday_dates'):
            reasoning.append(f"Staff on holiday: {len(availability_data['holiday_dates'])} affected dates")
        
        return {
            "success": True,
            "business_id": business_id,
            "roster_date": roster_date,
            "suggested_shifts": suggested_shifts,
            "positions_filled": positions_filled,
            "minimum_requirements": min_staff,
            "reasoning": reasoning,
            "total_available_staff": len(available_staff_details),
            "staff_on_holiday": len(available_staff) - len(available_staff_details)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Get business configuration and settings")
def get_business(business_id: str) -> Dict[str, Any]:
    """
    Get business configuration and settings.
    
    Args:
        business_id: The business identifier
    
    Returns:
        Dictionary with business details
    """
    try:
        table = dynamodb.Table(BUSINESS_TABLE)
        
        response = table.get_item(
            Key={'business_id': business_id}
        )
        
        if 'Item' not in response:
            return {
                "success": False,
                "error": f"Business {business_id} not found"
            }
        
        business = decimal_to_float(response['Item'])
        
        return {
            "success": True,
            "business": business
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Get staff with integrated availability and status")
def get_staff_with_availability(
    business_id: str,
    date: str,
    position: Optional[str] = None,
    available_only: bool = True
) -> Dict[str, Any]:
    """
    Get staff members with their availability and holiday status for a specific date.
    This combines multiple table queries for agent efficiency.
    
    Args:
        business_id: The business identifier
        date: Date to check (YYYY-MM-DD)
        position: Optional filter by position
        available_only: Only return available staff
    
    Returns:
        Dictionary with enriched staff data including availability
    """
    try:
        # Get all staff
        staff_data = get_staff(business_id, position, active_only=True)
        staff_list = staff_data.get('staff', [])
        
        # Get availability for the date
        availability_data = get_availability(business_id, date, date)
        availability_map = {
            a['staff_id'].split('#')[1] if '#' in a['staff_id'] else a['staff_id']: a 
            for a in availability_data.get('availability', [])
        }
        
        # Get holidays for the date
        holidays_data = get_holidays(business_id, None, date, date, "approved")
        holiday_staff = set()
        for holiday in holidays_data.get('holidays', []):
            staff_id = holiday['staff_id'].split('#')[1] if '#' in holiday['staff_id'] else holiday['staff_id']
            holiday_staff.add(staff_id)
        
        # Combine data
        enriched_staff = []
        for staff in staff_list:
            staff_id = staff['staff_id']
            availability = availability_map.get(staff_id, {})
            
            # Create enriched record
            enriched = {
                **staff,
                'availability_date': date,
                'available': availability.get('available', 'false') == 'true',  # Convert string to boolean for response
                'start_time': availability.get('start_time'),
                'end_time': availability.get('end_time'),
                'availability_notes': availability.get('notes'),
                'on_holiday': staff_id in holiday_staff,
                'full_staff_id': f"{business_id}#{staff_id}"
            }
            
            # Apply filters
            if available_only and not enriched['available']:
                continue
            if enriched['on_holiday']:
                enriched['available'] = False
                enriched['availability_notes'] = 'On approved holiday'
            
            enriched_staff.append(enriched)
        
        return {
            "success": True,
            "business_id": business_id,
            "date": date,
            "count": len(enriched_staff),
            "staff_with_availability": enriched_staff
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Get comprehensive roster generation context")
def get_roster_context(
    business_id: str,
    date: str
) -> Dict[str, Any]:
    """
    Get all information needed for intelligent roster generation in a single call.
    
    Args:
        business_id: The business identifier
        date: Date for roster (YYYY-MM-DD)
    
    Returns:
        Dictionary with complete context for roster generation
    """
    try:
        # Get business info
        business_data = get_business(business_id)
        business = business_data.get('business', {})
        
        # Get staff with availability
        staff_data = get_staff_with_availability(business_id, date, available_only=False)
        all_staff = staff_data.get('staff_with_availability', [])
        
        # Separate available and unavailable staff
        available_staff = [s for s in all_staff if s.get('available', False)]
        unavailable_staff = [s for s in all_staff if not s.get('available', False)]
        
        # Group by position
        staff_by_position = {}
        for staff in available_staff:
            position = staff.get('position', 'unknown')
            if position not in staff_by_position:
                staff_by_position[position] = []
            staff_by_position[position].append(staff)
        
        # Check for existing roster
        existing_roster = get_rosters(business_id, date, date)
        has_existing_roster = existing_roster.get('count', 0) > 0
        
        # Calculate staffing gaps
        min_requirements = {
            "manager": 1,
            "barista": 2, 
            "chef": 1
        }
        
        staffing_analysis = {}
        for position, required in min_requirements.items():
            available_count = len(staff_by_position.get(position, []))
            staffing_analysis[position] = {
                "required": required,
                "available": available_count,
                "shortage": max(0, required - available_count),
                "staff": staff_by_position.get(position, [])
            }
        
        return {
            "success": True,
            "business_id": business_id,
            "roster_date": date,
            "business_info": {
                "name": business.get('name'),
                "type": business.get('type'),
                "operating_hours": business.get('operating_hours', {})
            },
            "staffing_summary": {
                "total_staff": len(all_staff),
                "available_staff": len(available_staff),
                "unavailable_staff": len(unavailable_staff),
                "on_holiday": len([s for s in all_staff if s.get('on_holiday')])
            },
            "staff_by_position": staff_by_position,
            "staffing_analysis": staffing_analysis,
            "has_existing_roster": has_existing_roster,
            "existing_roster": existing_roster.get('rosters', []),
            "unavailable_reasons": [
                {
                    "staff_id": s['staff_id'],
                    "name": s['name'],
                    "position": s['position'],
                    "reason": "On holiday" if s.get('on_holiday') else "Not available",
                    "notes": s.get('availability_notes')
                }
                for s in unavailable_staff
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Search staff across multiple criteria")
def search_staff(
    business_id: str,
    criteria: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Advanced staff search with multiple criteria.
    
    Args:
        business_id: The business identifier
        criteria: Search criteria dictionary
            - positions: List of positions to include
            - experience_levels: List of experience levels
            - skills: List of required skills (staff must have at least one)
            - available_date: Check availability for specific date
            - min_hourly_rate: Minimum hourly rate
            - max_hourly_rate: Maximum hourly rate
    
    Returns:
        Dictionary with matching staff
    """
    try:
        # Get all active staff
        staff_data = get_staff(business_id, active_only=True)
        all_staff = staff_data.get('staff', [])
        
        # Apply filters
        filtered_staff = []
        for staff in all_staff:
            # Position filter
            if criteria.get('positions') and staff.get('position') not in criteria['positions']:
                continue
            
            # Experience filter
            if criteria.get('experience_levels') and staff.get('experience_level') not in criteria['experience_levels']:
                continue
            
            # Skills filter (staff must have at least one required skill)
            if criteria.get('skills'):
                staff_skills = set(staff.get('skills', []))
                required_skills = set(criteria['skills'])
                if not staff_skills.intersection(required_skills):
                    continue
            
            # Rate filters
            hourly_rate = float(staff.get('hourly_rate', 0))
            if criteria.get('min_hourly_rate') and hourly_rate < criteria['min_hourly_rate']:
                continue
            if criteria.get('max_hourly_rate') and hourly_rate > criteria['max_hourly_rate']:
                continue
            
            filtered_staff.append(staff)
        
        # If date criteria, check availability
        if criteria.get('available_date'):
            date = criteria['available_date']
            staff_with_availability = []
            
            for staff in filtered_staff:
                availability_data = get_availability(business_id, date, date, staff['staff_id'])
                availability = availability_data.get('availability', [])
                
                if availability and availability[0].get('available') == 'true':
                    staff['available_on_date'] = True
                    staff['availability_details'] = availability[0]
                    staff_with_availability.append(staff)
            
            filtered_staff = staff_with_availability
        
        return {
            "success": True,
            "business_id": business_id,
            "criteria": criteria,
            "count": len(filtered_staff),
            "matching_staff": filtered_staff
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Update staff member information")
def update_staff(
    business_id: str,
    staff_id: str,
    name: Optional[str] = None,
    position: Optional[str] = None,
    hourly_rate: Optional[float] = None,
    experience_level: Optional[str] = None,
    certifications: Optional[List[str]] = None,
    is_active: Optional[bool] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update existing staff member information.
    
    Args:
        business_id: The business identifier
        staff_id: The staff member identifier to update
        name: New name (optional)
        position: New position (optional)
        hourly_rate: New hourly rate (optional)
        experience_level: New experience level (optional)
        certifications: New certifications list (optional)
        is_active: New active status (optional)
        notes: Additional notes (optional)
    
    Returns:
        Dictionary with update status and updated staff information
    """
    try:
        table = dynamodb.Table(STAFF_TABLE)
        
        # First check if staff member exists
        existing_response = table.get_item(
            Key={
                'business_id': business_id,
                'staff_id': staff_id
            }
        )
        
        if 'Item' not in existing_response:
            return {
                "success": False,
                "error": f"Staff member {staff_id} not found for business {business_id}"
            }
        
        # Build update expression dynamically
        update_expression = "SET updated_at = :updated_at"
        expression_values = {":updated_at": datetime.now().isoformat()}
        
        if name is not None:
            update_expression += ", #name = :name"
            expression_values[":name"] = name
            
        if position is not None:
            update_expression += ", position = :position"
            expression_values[":position"] = position
            
        if hourly_rate is not None:
            update_expression += ", hourly_rate = :hourly_rate"
            expression_values[":hourly_rate"] = Decimal(str(hourly_rate))
            
        if experience_level is not None:
            update_expression += ", experience_level = :experience_level"
            expression_values[":experience_level"] = experience_level
            
        if certifications is not None:
            update_expression += ", certifications = :certifications"
            expression_values[":certifications"] = certifications
            
        if is_active is not None:
            update_expression += ", is_active = :is_active"
            expression_values[":is_active"] = 'true' if is_active else 'false'
            
        if notes is not None:
            update_expression += ", notes = :notes"
            expression_values[":notes"] = notes
        
        # Use ExpressionAttributeNames for reserved word 'name'
        expression_names = {"#name": "name"} if name is not None else None
        
        # Update the item
        update_params = {
            'Key': {
                'business_id': business_id,
                'staff_id': staff_id
            },
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        response = table.update_item(**update_params)
        
        updated_staff = decimal_to_float(response['Attributes'])
        
        return {
            "success": True,
            "message": f"Staff member {staff_id} updated successfully",
            "staff": updated_staff
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Approve or reject holiday requests")
def approve_holiday(
    business_id: str,
    staff_id: str,
    holiday_id: str,
    approved: bool,
    approver_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Approve or reject a staff holiday request.
    
    Args:
        business_id: The business identifier
        staff_id: The staff member identifier
        holiday_id: The holiday request identifier
        approved: True to approve, False to reject
        approver_notes: Optional notes from approver
    
    Returns:
        Dictionary with approval status and updated holiday information
    """
    try:
        table = dynamodb.Table(HOLIDAYS_TABLE)
        
        # First check if holiday request exists
        existing_response = table.get_item(
            Key={
                'staff_id': staff_id,
                'holiday_id': holiday_id
            }
        )
        
        if 'Item' not in existing_response:
            return {
                "success": False,
                "error": f"Holiday request {holiday_id} not found for staff {staff_id}"
            }
        
        holiday = existing_response['Item']
        
        # Verify business_id matches
        if holiday.get('business_id') != business_id:
            return {
                "success": False,
                "error": "Holiday request does not belong to the specified business"
            }
        
        # Update status and approval info
        status = "approved" if approved else "rejected"
        approval_date = datetime.now().isoformat()
        
        update_expression = "SET #status = :status, approval_date = :approval_date"
        expression_values = {
            ":status": status,
            ":approval_date": approval_date
        }
        expression_names = {"#status": "status"}
        
        if approver_notes:
            update_expression += ", approver_notes = :approver_notes"
            expression_values[":approver_notes"] = approver_notes
        
        response = table.update_item(
            Key={
                'staff_id': staff_id,
                'holiday_id': holiday_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_holiday = decimal_to_float(response['Attributes'])
        
        return {
            "success": True,
            "message": f"Holiday request {holiday_id} has been {'approved' if approved else 'rejected'}",
            "holiday": updated_holiday
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Update individual shift in roster")
def update_roster_shift(
    business_id: str,
    roster_date: str,
    staff_id: str,
    new_start_time: Optional[str] = None,
    new_end_time: Optional[str] = None,
    new_position: Optional[str] = None,
    remove_shift: bool = False
) -> Dict[str, Any]:
    """
    Update or remove an individual shift in an existing roster.
    
    Args:
        business_id: The business identifier
        roster_date: The roster date (YYYY-MM-DD format)
        staff_id: The staff member whose shift to modify
        new_start_time: New start time (HH:MM format, optional)
        new_end_time: New end time (HH:MM format, optional)
        new_position: New position for the shift (optional)
        remove_shift: True to remove the shift entirely
    
    Returns:
        Dictionary with update status and modified roster
    """
    try:
        table = dynamodb.Table(ROSTER_TABLE)
        
        # Get existing roster
        response = table.get_item(
            Key={
                'business_id': business_id,
                'roster_date': roster_date
            }
        )
        
        if 'Item' not in response:
            return {
                "success": False,
                "error": f"No roster found for {roster_date}"
            }
        
        roster = response['Item']
        shifts = roster.get('shifts', [])
        
        # Find the shift to modify
        shift_found = False
        updated_shifts = []
        total_cost = Decimal('0')
        
        for shift in shifts:
            if shift['staff_id'] == staff_id:
                shift_found = True
                if remove_shift:
                    # Skip this shift (remove it)
                    continue
                else:
                    # Update the shift
                    updated_shift = shift.copy()
                    if new_start_time:
                        updated_shift['start_time'] = new_start_time
                    if new_end_time:
                        updated_shift['end_time'] = new_end_time
                    if new_position:
                        updated_shift['position'] = new_position
                    
                    # Recalculate cost for this shift
                    start_hour = int(updated_shift['start_time'].split(':')[0])
                    end_hour = int(updated_shift['end_time'].split(':')[0])
                    hours = end_hour - start_hour
                    shift_cost = Decimal(str(updated_shift['hourly_rate'])) * Decimal(str(hours))
                    updated_shift['shift_cost'] = shift_cost
                    
                    updated_shifts.append(updated_shift)
                    total_cost += shift_cost
            else:
                # Keep other shifts unchanged
                updated_shifts.append(shift)
                total_cost += Decimal(str(shift.get('shift_cost', shift.get('cost', 0))))
        
        if not shift_found:
            return {
                "success": False,
                "error": f"No shift found for staff {staff_id} on {roster_date}"
            }
        
        # Update the roster
        update_response = table.update_item(
            Key={
                'business_id': business_id,
                'roster_date': roster_date
            },
            UpdateExpression="SET shifts = :shifts, total_cost = :total_cost, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":shifts": updated_shifts,
                ":total_cost": total_cost,
                ":updated_at": datetime.now().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_roster = decimal_to_float(update_response['Attributes'])
        
        action = "removed" if remove_shift else "updated"
        return {
            "success": True,
            "message": f"Shift for {staff_id} on {roster_date} has been {action}",
            "roster": updated_roster
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Copy roster from one date to another")
def copy_roster(
    business_id: str,
    source_date: str,
    target_date: str,
    check_availability: bool = True
) -> Dict[str, Any]:
    """
    Copy an existing roster to a new date, optionally checking staff availability.
    
    Args:
        business_id: The business identifier
        source_date: The date to copy from (YYYY-MM-DD format)
        target_date: The date to copy to (YYYY-MM-DD format)
        check_availability: Whether to verify staff availability on target date
    
    Returns:
        Dictionary with copy status and new roster information
    """
    try:
        roster_table = dynamodb.Table(ROSTER_TABLE)
        availability_table = dynamodb.Table(AVAILABILITY_TABLE)
        
        # Get source roster
        source_response = roster_table.get_item(
            Key={
                'business_id': business_id,
                'roster_date': source_date
            }
        )
        
        if 'Item' not in source_response:
            return {
                "success": False,
                "error": f"No roster found for source date {source_date}"
            }
        
        source_roster = source_response['Item']
        
        # Check if target roster already exists
        target_response = roster_table.get_item(
            Key={
                'business_id': business_id,
                'roster_date': target_date
            }
        )
        
        if 'Item' in target_response:
            return {
                "success": False,
                "error": f"Roster already exists for target date {target_date}"
            }
        
        # Copy shifts and check availability if requested
        copied_shifts = []
        unavailable_staff = []
        
        for shift in source_roster.get('shifts', []):
            staff_id = shift['staff_id']
            
            if check_availability:
                # Check if staff is available on target date
                availability_response = availability_table.get_item(
                    Key={
                        'staff_id': staff_id,
                        'date': target_date
                    }
                )
                
                if 'Item' not in availability_response or availability_response['Item'].get('available') != 'true':
                    unavailable_staff.append({
                        'staff_id': staff_id,
                        'name': shift.get('name', 'Unknown'),
                        'position': shift.get('position', 'Unknown')
                    })
                    continue
            
            # Copy the shift
            copied_shift = shift.copy()
            copied_shifts.append(copied_shift)
        
        # Create new roster
        new_roster = {
            'business_id': business_id,
            'roster_date': target_date,
            'shifts': copied_shifts,
            'total_cost': source_roster.get('total_cost', Decimal('0')),
            'status': 'draft',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'copied_from': source_date
        }
        
        # Save new roster
        roster_table.put_item(Item=new_roster)
        
        result = {
            "success": True,
            "message": f"Roster copied from {source_date} to {target_date}",
            "roster": decimal_to_float(new_roster),
            "copied_shifts": len(copied_shifts),
            "original_shifts": len(source_roster.get('shifts', []))
        }
        
        if unavailable_staff:
            result["warnings"] = {
                "unavailable_staff": unavailable_staff,
                "message": f"{len(unavailable_staff)} staff members were not available and their shifts were not copied"
            }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Calculate labor costs for roster")
def calculate_roster_costs(
    business_id: str,
    roster_date: str,
    include_breakdown: bool = True
) -> Dict[str, Any]:
    """
    Calculate detailed labor costs for a specific roster.
    
    Args:
        business_id: The business identifier
        roster_date: The roster date to calculate costs for
        include_breakdown: Whether to include per-staff breakdown
    
    Returns:
        Dictionary with cost calculations and breakdown
    """
    try:
        table = dynamodb.Table(ROSTER_TABLE)
        
        # Get roster
        response = table.get_item(
            Key={
                'business_id': business_id,
                'roster_date': roster_date
            }
        )
        
        if 'Item' not in response:
            return {
                "success": False,
                "error": f"No roster found for {roster_date}"
            }
        
        roster = response['Item']
        shifts = roster.get('shifts', [])
        
        if not shifts:
            return {
                "success": True,
                "total_cost": 0.0,
                "total_hours": 0.0,
                "staff_count": 0,
                "message": "No shifts scheduled for this date"
            }
        
        # Calculate totals
        total_cost = Decimal('0')
        total_hours = Decimal('0')
        position_breakdown = {}
        staff_breakdown = []
        
        for shift in shifts:
            # Calculate hours and cost for this shift
            start_time = shift['start_time']
            end_time = shift['end_time']
            hourly_rate = Decimal(str(shift.get('hourly_rate', 0)))
            
            start_hour = Decimal(str(start_time.split(':')[0])) + Decimal(str(start_time.split(':')[1])) / 60
            end_hour = Decimal(str(end_time.split(':')[0])) + Decimal(str(end_time.split(':')[1])) / 60
            hours = end_hour - start_hour
            
            # Use existing cost if available, otherwise calculate
            shift_cost = Decimal(str(shift.get('shift_cost', shift.get('cost', hourly_rate * hours))))
            
            total_cost += shift_cost
            total_hours += hours
            
            # Position breakdown
            position = shift.get('position', 'Unknown')
            if position not in position_breakdown:
                position_breakdown[position] = {
                    'hours': Decimal('0'),
                    'cost': Decimal('0'),
                    'staff_count': 0
                }
            position_breakdown[position]['hours'] += hours
            position_breakdown[position]['cost'] += shift_cost
            position_breakdown[position]['staff_count'] += 1
            
            # Staff breakdown
            if include_breakdown:
                staff_breakdown.append({
                    'staff_id': shift['staff_id'],
                    'name': shift.get('name', 'Unknown'),
                    'position': position,
                    'start_time': start_time,
                    'end_time': end_time,
                    'hours': float(hours),
                    'hourly_rate': float(hourly_rate),
                    'shift_cost': float(shift_cost)
                })
        
        result = {
            "success": True,
            "roster_date": roster_date,
            "total_cost": float(total_cost),
            "total_hours": float(total_hours),
            "staff_count": len(shifts),
            "average_hourly_rate": float(total_cost / total_hours) if total_hours > 0 else 0.0,
            "position_breakdown": {
                pos: {
                    "hours": float(data['hours']),
                    "cost": float(data['cost']),
                    "staff_count": data['staff_count'],
                    "avg_rate": float(data['cost'] / data['hours']) if data['hours'] > 0 else 0.0
                } for pos, data in position_breakdown.items()
            }
        }
        
        if include_breakdown:
            result["staff_breakdown"] = staff_breakdown
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(description="Check DynamoDB connection status")
def check_db_status() -> Dict[str, Any]:
    """
    Check if DynamoDB is accessible and tables exist.
    
    Returns:
        Dictionary with database status information
    """
    try:
        # Try to list tables
        existing_tables = list(dynamodb.tables.all())
        existing_table_names = [table.name for table in existing_tables]
        
        required_tables = [STAFF_TABLE, ROSTER_TABLE, AVAILABILITY_TABLE, BUSINESS_TABLE, HOLIDAYS_TABLE]
        missing_tables = [t for t in required_tables if t not in existing_table_names]
        
        return {
            "db_accessible": True,
            "endpoint": "AWS DynamoDB",
            "region": AWS_REGION,
            "existing_tables": existing_table_names,
            "required_tables": required_tables,
            "missing_tables": missing_tables,
            "all_tables_exist": len(missing_tables) == 0,
            "details": "Database is working" if len(missing_tables) == 0 else f"Missing tables: {', '.join(missing_tables)}"
        }
    except Exception as e:
        return {
            "db_accessible": False,
            "error": str(e),
            "endpoint": "AWS DynamoDB",
            "region": AWS_REGION
        }

@mcp.tool(description="Get staff member's certifications and compliance records")
def get_certifications(staff_id: str, business_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve certifications for a specific staff member.
    
    Args:
        staff_id: ID of staff member
        business_id: Optional business filter
        
    Returns:
        Dictionary containing certification records
    """
    try:
        table = dynamodb.Table(CERTIFICATIONS_TABLE)
        
        # Query by staff_id (primary key)
        response = table.query(
            KeyConditionExpression=Key('staff_id').eq(staff_id)
        )
        
        certifications = response.get('Items', [])
        
        # Filter by business if specified
        if business_id:
            certifications = [cert for cert in certifications if cert.get('business_id') == business_id]
        
        # Convert decimals to floats for JSON serialization
        certifications = json.loads(json.dumps(certifications, default=decimal_to_float))
        
        return {
            "certifications": certifications,
            "total_count": len(certifications),
            "staff_id": staff_id
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get certifications: {str(e)}",
            "certifications": []
        }

@mcp.tool(description="Get staff member's payroll history and payment records")
def get_payroll(staff_id: str, business_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Retrieve payroll records for a specific staff member.
    
    Args:
        staff_id: ID of staff member
        business_id: Optional business filter
        limit: Number of recent records to return (default: 10)
        
    Returns:
        Dictionary containing payroll records
    """
    try:
        table = dynamodb.Table(PAYROLL_TABLE)
        
        # Query by staff_id (primary key) with limit
        response = table.query(
            KeyConditionExpression=Key('staff_id').eq(staff_id),
            Limit=limit,
            ScanIndexForward=False  # Most recent first
        )
        
        payroll_records = response.get('Items', [])
        
        # Filter by business if specified
        if business_id:
            payroll_records = [record for record in payroll_records if record.get('business_id') == business_id]
        
        # Convert decimals to floats for JSON serialization
        payroll_records = json.loads(json.dumps(payroll_records, default=decimal_to_float))
        
        return {
            "payroll_records": payroll_records,
            "total_count": len(payroll_records),
            "staff_id": staff_id
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get payroll records: {str(e)}",
            "payroll_records": []
        }

@mcp.tool(description="Get staff member's training history and course completions")
def get_training(staff_id: str, business_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve training records for a specific staff member.
    
    Args:
        staff_id: ID of staff member
        business_id: Optional business filter
        
    Returns:
        Dictionary containing training records
    """
    try:
        table = dynamodb.Table(TRAINING_TABLE)
        
        # Query by staff_id (primary key)
        response = table.query(
            KeyConditionExpression=Key('staff_id').eq(staff_id)
        )
        
        training_records = response.get('Items', [])
        
        # Filter by business if specified
        if business_id:
            training_records = [record for record in training_records if record.get('business_id') == business_id]
        
        # Sort by completion date (most recent first)
        training_records.sort(key=lambda x: x.get('completion_date', ''), reverse=True)
        
        # Convert decimals to floats for JSON serialization
        training_records = json.loads(json.dumps(training_records, default=decimal_to_float))
        
        return {
            "training_records": training_records,
            "total_count": len(training_records),
            "staff_id": staff_id
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get training records: {str(e)}",
            "training_records": []
        }

if __name__ == "__main__":
    print("👥 StaffCast DynamoDB MCP Server")
    print("=" * 50)
    
    # Check database connection
    status = check_db_status()
    if status['db_accessible']:
        print(f"✓ Connected to: {status['endpoint']}")
        print(f"✓ Region: {status['region']}")
        if status['all_tables_exist']:
            print("✓ All required tables exist")
        else:
            print(f"⚠️  Missing tables: {', '.join(status['missing_tables'])}")
    else:
        print(f"❌ Failed to connect to DynamoDB: {status['error']}")
    
    print("\n📝 Available tools:")
    print("  Basic Operations:")
    print("    - list_tables: List all DynamoDB tables")
    print("    - check_db_status: Check database connection")
    print("  Staff Management:")
    print("    - get_staff: Get staff members for a business")
    print("    - add_staff: Add a new staff member")
    print("    - update_staff: Update existing staff information")
    print("    - search_staff: Advanced staff search with multiple criteria")
    print("  Availability & Holidays:")
    print("    - get_availability: Check staff availability")
    print("    - set_availability: Set staff availability")
    print("    - get_holidays: Get staff holiday requests")
    print("    - add_holiday: Add a holiday request")
    print("    - approve_holiday: Approve or reject holiday requests")
    print("  Roster Management:")
    print("    - get_rosters: Get roster data")
    print("    - save_roster: Create or update a roster")
    print("    - suggest_roster: Generate roster suggestions")
    print("    - update_roster_shift: Modify or remove individual shifts")
    print("    - copy_roster: Copy roster from one date to another")
    print("    - calculate_roster_costs: Calculate detailed labor costs")
    print("  Agent-Optimized Queries:")
    print("    - get_staff_with_availability: Staff with integrated availability status")
    print("    - get_roster_context: Complete context for roster generation")
    print("  Business Configuration:")
    print("    - get_business: Get business configuration")
    
    print(f"\nServer will run at http://{MCP_HOST}:{MCP_PORT}/sse")
    print(f"(Using FASTMCP_PORT={MCP_PORT} environment variable)")
    
    # Run with SSE transport for Strands
    mcp.run(transport="sse")