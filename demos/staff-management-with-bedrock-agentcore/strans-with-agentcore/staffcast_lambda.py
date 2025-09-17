import json
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Table names - Core tables
STAFF_TABLE = 'staffcast-dev-staff'
ROSTER_TABLE = 'staffcast-dev-rosters'
AVAILABILITY_TABLE = 'staffcast-dev-availability'
BUSINESS_TABLE = 'staffcast-dev-businesses'
HOLIDAYS_TABLE = 'staffcast-dev-holidays'

# Extension tables
CERTIFICATIONS_TABLE = 'staffcast-dev-certifications'
PAYROLL_TABLE = 'staffcast-dev-payroll'
TRAINING_TABLE = 'staffcast-dev-training'

def lambda_handler(event, context):
    """Lambda handler for StaffCast MCP tools"""
    try:
        tool_name = event.get('name', '')
        arguments = event.get('arguments', {})
        
        # Route to appropriate function
        handlers = {
            'list_tables_tool': list_tables,
            'get_staff_tool': get_staff,
            'add_staff_tool': add_staff,
            'get_holidays_tool': get_holidays,
            'add_holiday_tool': add_holiday,
            'get_availability_tool': get_availability,
            'set_availability_tool': set_availability,
            'get_rosters_tool': get_rosters,
            'save_roster_tool': save_roster,
            'suggest_roster_tool': suggest_roster,
            'get_business_tool': get_business,
            'get_staff_with_availability_tool': get_staff_with_availability,
            'get_roster_context_tool': get_roster_context,
            'search_staff_tool': search_staff,
            'update_staff_tool': update_staff,
            'approve_holiday_tool': approve_holiday,
            'update_roster_shift_tool': update_roster_shift,
            'copy_roster_tool': copy_roster,
            'calculate_roster_costs_tool': calculate_roster_costs,
            'check_db_status_tool': check_db_status,
            'get_certifications_tool': get_certifications,
            'get_payroll_tool': get_payroll,
            'get_training_tool': get_training
        }
        
        if tool_name in handlers:
            return handlers[tool_name](arguments)
        else:
            return error_response(f'Unknown tool: {tool_name}')
            
    except Exception as e:
        return error_response(str(e))

def success_response(data):
    """Standard success response"""
    return {
        'statusCode': 200,
        'body': json.dumps(data, default=decimal_default)
    }

def error_response(message):
    """Standard error response"""
    return {
        'statusCode': 500,
        'body': json.dumps({'success': False, 'error': message})
    }

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def decimal_to_float(obj):
    """Convert Decimal objects to float recursively"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj

def list_tables(arguments):
    """List all DynamoDB tables"""
    try:
        tables = []
        expected_tables = {
            STAFF_TABLE: "Staff members",
            ROSTER_TABLE: "Work rosters", 
            AVAILABILITY_TABLE: "Staff availability",
            BUSINESS_TABLE: "Business configurations",
            HOLIDAYS_TABLE: "Staff holidays",
            CERTIFICATIONS_TABLE: "Staff certifications",
            PAYROLL_TABLE: "Staff payroll records",
            TRAINING_TABLE: "Staff training records"
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
        
        return success_response({
            "success": True,
            "tables": tables,
            "total": len(tables)
        })
    except Exception as e:
        return error_response(str(e))

def get_staff(arguments):
    """Get staff members for a business"""
    try:
        business_id = arguments.get('business_id', 'cafe-001')
        position = arguments.get('position')
        active_only = arguments.get('active_only', True)
        
        table = dynamodb.Table(STAFF_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('business_id').eq(business_id)
        )
        
        staff = response.get('Items', [])
        
        # Apply filters
        if position:
            staff = [s for s in staff if s.get('position') == position]
        
        if active_only:
            staff = [s for s in staff if s.get('is_active', 'true') == 'true']
        
        # Calculate tenure
        for member in staff:
            if 'hire_date' in member:
                hire_date = datetime.fromisoformat(member['hire_date'].replace('Z', '+00:00'))
                tenure_days = (datetime.utcnow() - hire_date).days
                member['tenure_days'] = tenure_days
                member['tenure_text'] = f"{tenure_days // 365} years, {(tenure_days % 365) // 30} months"
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "count": len(staff),
            "staff": staff
        })
    except Exception as e:
        return error_response(str(e))

def add_staff(arguments):
    """Add a new staff member"""
    try:
        table = dynamodb.Table(STAFF_TABLE)
        
        item = {
            'business_id': arguments['business_id'],
            'staff_id': arguments['staff_id'],
            'name': arguments['name'],
            'position': arguments['position'],
            'email': arguments['email'],
            'phone': arguments['phone'],
            'experience_level': arguments.get('experience_level', 'junior'),
            'hourly_rate': Decimal(str(arguments.get('hourly_rate', 25.0))),
            'skills': arguments.get('skills', []),
            'preferred_hours': arguments.get('preferred_hours', 40),
            'shifts_available': arguments.get('shifts_available', ["morning", "afternoon", "evening"]),
            'is_active': 'true',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'hire_date': arguments.get('hire_date', datetime.utcnow().isoformat())
        }
        
        if arguments.get('emergency_contact'):
            item['emergency_contact'] = arguments['emergency_contact']
        if arguments.get('certifications'):
            item['certifications'] = arguments['certifications']
        if arguments.get('notes'):
            item['notes'] = arguments['notes']
        
        table.put_item(Item=item)
        
        return success_response({
            "success": True,
            "message": f"Staff member {arguments['name']} added successfully",
            "staff": item
        })
    except Exception as e:
        return error_response(str(e))

def get_holidays(arguments):
    """Get staff holidays"""
    try:
        business_id = arguments['business_id']
        staff_id = arguments.get('staff_id')
        start_date = arguments.get('start_date')
        end_date = arguments.get('end_date')
        status = arguments.get('status')
        
        table = dynamodb.Table(HOLIDAYS_TABLE)
        
        if staff_id:
            response = table.query(
                KeyConditionExpression=Key('staff_id').eq(f"{business_id}#{staff_id}")
            )
        else:
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
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "count": len(holidays),
            "holidays": holidays
        })
    except Exception as e:
        return error_response(str(e))

def add_holiday(arguments):
    """Add a holiday request"""
    try:
        table = dynamodb.Table(HOLIDAYS_TABLE)
        
        business_id = arguments['business_id']
        staff_id = arguments['staff_id']
        start_date = arguments['start_date']
        end_date = arguments['end_date']
        
        # Calculate days
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
            'type': arguments.get('type', 'annual_leave'),
            'status': arguments.get('status', 'pending'),
            'requested_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if arguments.get('reason'):
            item['reason'] = arguments['reason']
        
        table.put_item(Item=item)
        
        return success_response({
            "success": True,
            "message": f"Holiday request added for {staff_id}",
            "holiday": item
        })
    except Exception as e:
        return error_response(str(e))

def get_availability(arguments):
    """Get staff availability"""
    try:
        business_id = arguments['business_id']
        start_date = arguments['start_date']
        end_date = arguments['end_date']
        staff_id = arguments.get('staff_id')
        
        table = dynamodb.Table(AVAILABILITY_TABLE)
        
        if staff_id:
            response = table.query(
                KeyConditionExpression=Key('staff_id').eq(f"{business_id}#{staff_id}") & 
                                     Key('date').between(start_date, end_date)
            )
        else:
            response = table.scan(
                FilterExpression=Attr('business_id').eq(business_id) & 
                               Attr('date').between(start_date, end_date)
            )
        
        availability = response.get('Items', [])
        
        # Check for holidays
        holidays_args = {'business_id': business_id, 'start_date': start_date, 'end_date': end_date, 'status': 'approved'}
        holidays_response = get_holidays(holidays_args)
        holidays_data = json.loads(holidays_response['body'])
        
        holiday_dates = set()
        for holiday in holidays_data.get('holidays', []):
            h_start = datetime.strptime(holiday['start_date'], '%Y-%m-%d')
            h_end = datetime.strptime(holiday['end_date'], '%Y-%m-%d')
            current = h_start
            while current <= h_end:
                holiday_dates.add(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        
        # Mark holiday dates
        for avail in availability:
            if avail['date'] in holiday_dates:
                avail['on_holiday'] = True
                avail['available'] = 'false'
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(availability),
            "availability": availability,
            "holiday_dates": list(holiday_dates)
        })
    except Exception as e:
        return error_response(str(e))

def set_availability(arguments):
    """Set staff availability"""
    try:
        table = dynamodb.Table(AVAILABILITY_TABLE)
        
        business_id = arguments['business_id']
        staff_id = arguments['staff_id']
        date = arguments['date']
        available = arguments['available']
        
        item = {
            'staff_id': f"{business_id}#{staff_id}",
            'date': date,
            'business_id': business_id,
            'available': 'true' if available else 'false',
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if available and arguments.get('start_time') and arguments.get('end_time'):
            item['start_time'] = arguments['start_time']
            item['end_time'] = arguments['end_time']
        
        if arguments.get('notes'):
            item['notes'] = arguments['notes']
        
        table.put_item(Item=item)
        
        return success_response({
            "success": True,
            "message": f"Availability updated for {staff_id} on {date}",
            "availability": item
        })
    except Exception as e:
        return error_response(str(e))

def get_rosters(arguments):
    """Get rosters for a date range"""
    try:
        business_id = arguments['business_id']
        start_date = arguments['start_date']
        end_date = arguments.get('end_date', start_date)
        status = arguments.get('status')
        
        table = dynamodb.Table(ROSTER_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('business_id').eq(business_id) & 
                                 Key('roster_date').between(start_date, end_date)
        )
        
        rosters = response.get('Items', [])
        
        if status:
            rosters = [r for r in rosters if r.get('status') == status]
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(rosters),
            "rosters": rosters
        })
    except Exception as e:
        return error_response(str(e))

def save_roster(arguments):
    """Create or update a roster"""
    try:
        table = dynamodb.Table(ROSTER_TABLE)
        staff_table = dynamodb.Table(STAFF_TABLE)
        
        business_id = arguments['business_id']
        roster_date = arguments['roster_date']
        shifts = arguments['shifts']
        
        # Calculate totals and enrich shifts
        total_hours = 0
        total_cost = 0
        
        for shift in shifts:
            # Get staff details
            staff_response = staff_table.get_item(
                Key={'business_id': business_id, 'staff_id': shift['staff_id']}
            )
            
            if 'Item' in staff_response:
                staff = staff_response['Item']
                shift['staff_name'] = staff['name']
                shift['name'] = staff['name']
                hourly_rate = float(staff.get('hourly_rate', 0))
                shift['hourly_rate'] = Decimal(str(hourly_rate))
                
                # Calculate hours
                start = datetime.strptime(shift['start_time'], '%H:%M')
                end = datetime.strptime(shift['end_time'], '%H:%M')
                hours = (end - start).total_seconds() / 3600
                hours -= shift.get('break_duration', 30) / 60
                
                shift['hours'] = Decimal(str(hours))
                shift_cost = hours * hourly_rate
                shift['shift_cost'] = Decimal(str(shift_cost))
                
                total_hours += hours
                total_cost += shift_cost
        
        item = {
            'business_id': business_id,
            'roster_date': roster_date,
            'shifts': shifts,
            'status': arguments.get('status', 'draft'),
            'total_hours': Decimal(str(total_hours)),
            'total_cost': Decimal(str(total_cost)),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if arguments.get('notes'):
            item['notes'] = arguments['notes']
        if arguments.get('weather_forecast'):
            item['weather_forecast'] = arguments['weather_forecast']
        
        table.put_item(Item=item)
        
        return success_response({
            "success": True,
            "message": f"Roster saved for {roster_date}",
            "roster": item
        })
    except Exception as e:
        return error_response(str(e))

def suggest_roster(arguments):
    """Generate roster suggestions"""
    try:
        business_id = arguments['business_id']
        roster_date = arguments['roster_date']
        expected_customers = arguments.get('expected_customers')
        weather_conditions = arguments.get('weather_conditions')
        special_events = arguments.get('special_events', [])
        min_staff = arguments.get('min_staff', {"manager": 1, "barista": 2, "chef": 1})
        
        # Get available staff
        availability_args = {'business_id': business_id, 'start_date': roster_date, 'end_date': roster_date}
        availability_response = get_availability(availability_args)
        availability_data = json.loads(availability_response['body'])
        available_staff = availability_data.get('availability', [])
        
        # Get all staff
        staff_args = {'business_id': business_id}
        staff_response = get_staff(staff_args)
        staff_data = json.loads(staff_response['body'])
        all_staff = {s['staff_id']: s for s in staff_data.get('staff', [])}
        
        # Filter available staff
        available_staff_ids = {
            a['staff_id'].split('#')[1] 
            for a in available_staff 
            if a.get('available') and not a.get('on_holiday', False)
        }
        available_staff_details = [all_staff[sid] for sid in available_staff_ids if sid in all_staff]
        
        # Adjust requirements based on parameters
        if expected_customers and expected_customers > 200:
            min_staff["barista"] = 3
            min_staff["chef"] = 2
        
        if weather_conditions in ["sunny", "warm"]:
            min_staff["barista"] = max(min_staff.get("barista", 2), 3)
        
        if special_events:
            for position in min_staff:
                min_staff[position] = int(min_staff[position] * 1.5)
        
        # Build suggestions
        suggested_shifts = []
        positions_filled = {pos: 0 for pos in min_staff}
        
        # Sort by experience and tenure
        experience_order = {"senior": 1, "intermediate": 2, "junior": 3}
        available_staff_details.sort(
            key=lambda x: (
                experience_order.get(x.get('experience_level', 'junior'), 4),
                -x.get('tenure_days', 0),
                x.get('name')
            )
        )
        
        # Assign shifts
        for staff in available_staff_details:
            position = staff.get('position')
            if position in positions_filled and positions_filled[position] < min_staff.get(position, 0):
                shifts_available = staff.get('shifts_available', ["morning", "afternoon", "evening"])
                
                if "morning" in shifts_available and positions_filled[position] == 0:
                    shift_times = {"manager": ("08:00", "16:00"), "barista": ("06:00", "14:00"), "chef": ("06:00", "14:00")}
                elif "afternoon" in shifts_available:
                    shift_times = {"manager": ("12:00", "20:00"), "barista": ("11:00", "19:00"), "chef": ("12:00", "20:00")}
                else:
                    shift_times = {"manager": ("14:00", "22:00"), "barista": ("14:00", "22:00"), "chef": ("14:00", "22:00")}
                
                start, end = shift_times.get(position, ("09:00", "17:00"))
                
                suggested_shifts.append({
                    "staff_id": staff['staff_id'],
                    "staff_name": staff['name'],
                    "name": staff['name'],
                    "position": position,
                    "start_time": start,
                    "end_time": end,
                    "break_duration": 30,
                    "experience_level": staff.get('experience_level', 'junior'),
                    "hourly_rate": staff.get('hourly_rate', 0)
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
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "roster_date": roster_date,
            "suggested_shifts": suggested_shifts,
            "positions_filled": positions_filled,
            "minimum_requirements": min_staff,
            "reasoning": reasoning,
            "total_available_staff": len(available_staff_details)
        })
    except Exception as e:
        return error_response(str(e))

def get_business(arguments):
    """Get business configuration"""
    try:
        business_id = arguments['business_id']
        table = dynamodb.Table(BUSINESS_TABLE)
        
        response = table.get_item(Key={'business_id': business_id})
        
        if 'Item' not in response:
            return error_response(f"Business {business_id} not found")
        
        return success_response({
            "success": True,
            "business": response['Item']
        })
    except Exception as e:
        return error_response(str(e))

def check_db_status(arguments):
    """Check database status"""
    try:
        existing_tables = list(dynamodb.tables.all())
        existing_table_names = [table.name for table in existing_tables]
        
        required_tables = [STAFF_TABLE, ROSTER_TABLE, AVAILABILITY_TABLE, BUSINESS_TABLE, HOLIDAYS_TABLE, 
                          CERTIFICATIONS_TABLE, PAYROLL_TABLE, TRAINING_TABLE]
        missing_tables = [t for t in required_tables if t not in existing_table_names]
        
        return success_response({
            "db_accessible": True,
            "existing_tables": existing_table_names,
            "required_tables": required_tables,
            "missing_tables": missing_tables,
            "all_tables_exist": len(missing_tables) == 0
        })
    except Exception as e:
        return error_response(str(e))

def get_staff_with_availability(arguments):
    """Get staff with availability for a specific date"""
    try:
        business_id = arguments['business_id']
        date = arguments['date']
        position = arguments.get('position')
        available_only = arguments.get('available_only', True)
        
        # Get staff
        staff_args = {'business_id': business_id, 'position': position, 'active_only': True}
        staff_response = get_staff(staff_args)
        staff_data = json.loads(staff_response['body'])
        staff_list = staff_data.get('staff', [])
        
        # Get availability
        availability_args = {'business_id': business_id, 'start_date': date, 'end_date': date}
        availability_response = get_availability(availability_args)
        availability_data = json.loads(availability_response['body'])
        availability_map = {
            a['staff_id'].split('#')[1] if '#' in a['staff_id'] else a['staff_id']: a 
            for a in availability_data.get('availability', [])
        }
        
        # Get holidays
        holidays_args = {'business_id': business_id, 'start_date': date, 'end_date': date, 'status': 'approved'}
        holidays_response = get_holidays(holidays_args)
        holidays_data = json.loads(holidays_response['body'])
        holiday_staff = set()
        for holiday in holidays_data.get('holidays', []):
            staff_id = holiday['staff_id'].split('#')[1] if '#' in holiday['staff_id'] else holiday['staff_id']
            holiday_staff.add(staff_id)
        
        # Combine data
        enriched_staff = []
        for staff in staff_list:
            staff_id = staff['staff_id']
            availability = availability_map.get(staff_id, {})
            
            enriched = {
                **staff,
                'availability_date': date,
                'available': availability.get('available', 'false') == 'true',
                'start_time': availability.get('start_time'),
                'end_time': availability.get('end_time'),
                'availability_notes': availability.get('notes'),
                'on_holiday': staff_id in holiday_staff,
                'full_staff_id': f"{business_id}#{staff_id}"
            }
            
            if available_only and not enriched['available']:
                continue
            if enriched['on_holiday']:
                enriched['available'] = False
                enriched['availability_notes'] = 'On approved holiday'
            
            enriched_staff.append(enriched)
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "date": date,
            "count": len(enriched_staff),
            "staff_with_availability": enriched_staff
        })
    except Exception as e:
        return error_response(str(e))

def get_roster_context(arguments):
    """Get comprehensive roster context"""
    try:
        business_id = arguments['business_id']
        date = arguments['date']
        
        # Get business info
        business_args = {'business_id': business_id}
        business_response = get_business(business_args)
        business_data = json.loads(business_response['body'])
        business = business_data.get('business', {})
        
        # Get staff with availability
        staff_args = {'business_id': business_id, 'date': date, 'available_only': False}
        staff_response = get_staff_with_availability(staff_args)
        staff_data = json.loads(staff_response['body'])
        all_staff = staff_data.get('staff_with_availability', [])
        
        available_staff = [s for s in all_staff if s.get('available', False)]
        unavailable_staff = [s for s in all_staff if not s.get('available', False)]
        
        # Group by position
        staff_by_position = {}
        for staff in available_staff:
            position = staff.get('position', 'unknown')
            if position not in staff_by_position:
                staff_by_position[position] = []
            staff_by_position[position].append(staff)
        
        # Check existing roster
        roster_args = {'business_id': business_id, 'start_date': date, 'end_date': date}
        existing_roster_response = get_rosters(roster_args)
        existing_roster_data = json.loads(existing_roster_response['body'])
        has_existing_roster = existing_roster_data.get('count', 0) > 0
        
        # Staffing analysis
        min_requirements = {"manager": 1, "barista": 2, "chef": 1}
        staffing_analysis = {}
        for position, required in min_requirements.items():
            available_count = len(staff_by_position.get(position, []))
            staffing_analysis[position] = {
                "required": required,
                "available": available_count,
                "shortage": max(0, required - available_count),
                "staff": staff_by_position.get(position, [])
            }
        
        return success_response({
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
            "existing_roster": existing_roster_data.get('rosters', [])
        })
    except Exception as e:
        return error_response(str(e))

# Placeholder functions for remaining tools
def search_staff(arguments):
    """Search staff across multiple criteria"""
    try:
        business_id = arguments['business_id']
        name_query = arguments.get('name_query', '').lower()
        position = arguments.get('position')
        experience_level = arguments.get('experience_level')
        skills = arguments.get('skills', [])
        
        table = dynamodb.Table(STAFF_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('business_id').eq(business_id)
        )
        
        staff = response.get('Items', [])
        
        # Apply filters
        if name_query:
            staff = [s for s in staff if name_query in s.get('name', '').lower()]
        
        if position:
            staff = [s for s in staff if s.get('position') == position]
            
        if experience_level:
            staff = [s for s in staff if s.get('experience_level') == experience_level]
            
        if skills:
            staff = [s for s in staff if any(skill in s.get('skills', []) for skill in skills)]
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "search_criteria": {
                "name_query": name_query,
                "position": position,
                "experience_level": experience_level,
                "skills": skills
            },
            "results_count": len(staff),
            "staff": decimal_to_float(staff)
        })
    except Exception as e:
        return error_response(str(e))

def update_staff(arguments):
    """Update staff member information"""
    try:
        business_id = arguments['business_id']
        staff_id = arguments['staff_id']
        
        table = dynamodb.Table(STAFF_TABLE)
        
        # First check if staff member exists
        existing_response = table.get_item(
            Key={'business_id': business_id, 'staff_id': staff_id}
        )
        
        if 'Item' not in existing_response:
            return error_response(f"Staff member {staff_id} not found for business {business_id}")
        
        # Build update expression dynamically
        update_expression = "SET updated_at = :updated_at"
        expression_values = {":updated_at": datetime.utcnow().isoformat()}
        expression_names = {}
        
        if 'name' in arguments:
            update_expression += ", #name = :name"
            expression_values[":name"] = arguments['name']
            expression_names["#name"] = "name"
            
        if 'position' in arguments:
            update_expression += ", position = :position"
            expression_values[":position"] = arguments['position']
            
        if 'hourly_rate' in arguments:
            update_expression += ", hourly_rate = :hourly_rate"
            expression_values[":hourly_rate"] = Decimal(str(arguments['hourly_rate']))
            
        if 'experience_level' in arguments:
            update_expression += ", experience_level = :experience_level"
            expression_values[":experience_level"] = arguments['experience_level']
            
        if 'certifications' in arguments:
            update_expression += ", certifications = :certifications"
            expression_values[":certifications"] = arguments['certifications']
            
        if 'is_active' in arguments:
            update_expression += ", is_active = :is_active"
            expression_values[":is_active"] = 'true' if arguments['is_active'] else 'false'
            
        if 'notes' in arguments:
            update_expression += ", notes = :notes"
            expression_values[":notes"] = arguments['notes']
        
        # Update the item
        update_params = {
            'Key': {'business_id': business_id, 'staff_id': staff_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        response = table.update_item(**update_params)
        
        return success_response({
            "success": True,
            "message": f"Staff member {staff_id} updated successfully",
            "staff": decimal_to_float(response['Attributes'])
        })
        
    except Exception as e:
        return error_response(str(e))

def approve_holiday(arguments):
    """Approve or reject holiday requests"""
    try:
        business_id = arguments['business_id']
        staff_id = arguments['staff_id']
        holiday_id = arguments['holiday_id']
        status = arguments['status']  # 'approved' or 'rejected'
        
        table = dynamodb.Table(HOLIDAYS_TABLE)
        
        # Update holiday status
        response = table.update_item(
            Key={
                'staff_id': f"{business_id}#{staff_id}",
                'holiday_id': holiday_id
            },
            UpdateExpression="SET #status = :status, updated_at = :updated_at, approved_by = :approved_by",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": status,
                ":updated_at": datetime.utcnow().isoformat(),
                ":approved_by": arguments.get('approved_by', 'system')
            },
            ReturnValues='ALL_NEW'
        )
        
        if arguments.get('rejection_reason') and status == 'rejected':
            table.update_item(
                Key={
                    'staff_id': f"{business_id}#{staff_id}",
                    'holiday_id': holiday_id
                },
                UpdateExpression="SET rejection_reason = :reason",
                ExpressionAttributeValues={":reason": arguments['rejection_reason']}
            )
        
        return success_response({
            "success": True,
            "message": f"Holiday request {status} for {staff_id}",
            "holiday": decimal_to_float(response['Attributes'])
        })
        
    except Exception as e:
        return error_response(str(e))

def update_roster_shift(arguments):
    """Update individual shift in roster"""
    try:
        business_id = arguments['business_id']
        roster_date = arguments['roster_date']
        shift_index = arguments['shift_index']
        
        table = dynamodb.Table(ROSTER_TABLE)
        
        # Get existing roster
        response = table.get_item(
            Key={'business_id': business_id, 'roster_date': roster_date}
        )
        
        if 'Item' not in response:
            return error_response(f"Roster not found for {roster_date}")
        
        roster = response['Item']
        shifts = roster.get('shifts', [])
        
        if shift_index >= len(shifts):
            return error_response(f"Shift index {shift_index} out of range")
        
        # Update shift fields
        shift = shifts[shift_index]
        if 'start_time' in arguments:
            shift['start_time'] = arguments['start_time']
        if 'end_time' in arguments:
            shift['end_time'] = arguments['end_time']
        if 'break_duration' in arguments:
            shift['break_duration'] = arguments['break_duration']
        if 'notes' in arguments:
            shift['notes'] = arguments['notes']
        
        # Recalculate shift cost if times changed
        if 'start_time' in arguments or 'end_time' in arguments:
            start = datetime.strptime(shift['start_time'], '%H:%M')
            end = datetime.strptime(shift['end_time'], '%H:%M')
            hours = (end - start).total_seconds() / 3600
            hours -= shift.get('break_duration', 30) / 60
            
            shift['hours'] = Decimal(str(hours))
            hourly_rate = float(shift.get('hourly_rate', 0))
            shift['shift_cost'] = Decimal(str(hours * hourly_rate))
        
        # Update roster
        table.update_item(
            Key={'business_id': business_id, 'roster_date': roster_date},
            UpdateExpression="SET shifts = :shifts, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":shifts": shifts,
                ":updated_at": datetime.utcnow().isoformat()
            }
        )
        
        return success_response({
            "success": True,
            "message": f"Shift {shift_index} updated for {roster_date}",
            "updated_shift": decimal_to_float(shift)
        })
        
    except Exception as e:
        return error_response(str(e))

def copy_roster(arguments):
    """Copy roster from one date to another"""
    try:
        business_id = arguments['business_id']
        source_date = arguments['source_date']
        target_date = arguments['target_date']
        
        table = dynamodb.Table(ROSTER_TABLE)
        
        # Get source roster
        source_response = table.get_item(
            Key={'business_id': business_id, 'roster_date': source_date}
        )
        
        if 'Item' not in source_response:
            return error_response(f"Source roster not found for {source_date}")
        
        source_roster = source_response['Item']
        
        # Create new roster for target date
        new_roster = {
            'business_id': business_id,
            'roster_date': target_date,
            'shifts': source_roster['shifts'],
            'status': 'draft',
            'total_hours': source_roster.get('total_hours', 0),
            'total_cost': source_roster.get('total_cost', 0),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'copied_from': source_date
        }
        
        if arguments.get('notes'):
            new_roster['notes'] = arguments['notes']
        
        table.put_item(Item=new_roster)
        
        return success_response({
            "success": True,
            "message": f"Roster copied from {source_date} to {target_date}",
            "roster": decimal_to_float(new_roster)
        })
        
    except Exception as e:
        return error_response(str(e))

def calculate_roster_costs(arguments):
    """Calculate labor costs for roster"""
    try:
        business_id = arguments['business_id']
        roster_date = arguments['roster_date']
        
        table = dynamodb.Table(ROSTER_TABLE)
        
        # Get roster
        response = table.get_item(
            Key={'business_id': business_id, 'roster_date': roster_date}
        )
        
        if 'Item' not in response:
            return error_response(f"Roster not found for {roster_date}")
        
        roster = response['Item']
        shifts = roster.get('shifts', [])
        
        # Calculate detailed costs
        total_hours = 0
        total_cost = 0
        cost_by_position = {}
        
        for shift in shifts:
            position = shift.get('position', 'unknown')
            hours = float(shift.get('hours', 0))
            hourly_rate = float(shift.get('hourly_rate', 0))
            shift_cost = hours * hourly_rate
            
            total_hours += hours
            total_cost += shift_cost
            
            if position not in cost_by_position:
                cost_by_position[position] = {'hours': 0, 'cost': 0, 'staff_count': 0}
            
            cost_by_position[position]['hours'] += hours
            cost_by_position[position]['cost'] += shift_cost
            cost_by_position[position]['staff_count'] += 1
        
        return success_response({
            "success": True,
            "business_id": business_id,
            "roster_date": roster_date,
            "cost_analysis": {
                "total_hours": total_hours,
                "total_cost": total_cost,
                "average_hourly_rate": total_cost / total_hours if total_hours > 0 else 0,
                "cost_by_position": cost_by_position,
                "shift_count": len(shifts)
            }
        })
        
    except Exception as e:
        return error_response(str(e))

def get_certifications(arguments):
    """Get staff member's certifications and compliance records"""
    try:
        staff_id = arguments['staff_id']
        business_id = arguments.get('business_id')
        
        table = dynamodb.Table(CERTIFICATIONS_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('staff_id').eq(staff_id)
        )
        
        certifications = response.get('Items', [])
        
        # Filter by business if provided
        if business_id:
            certifications = [c for c in certifications if c.get('business_id') == business_id]
        
        # Categorize certifications
        active_certs = [c for c in certifications if c.get('status') == 'active']
        expired_certs = [c for c in certifications if c.get('status') == 'expired']
        expiring_soon = []
        
        # Check for expiring certifications (within 30 days)
        cutoff_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
        for cert in active_certs:
            if cert.get('expiry_date') and cert['expiry_date'] <= cutoff_date:
                expiring_soon.append(cert)
        
        return success_response({
            "success": True,
            "staff_id": staff_id,
            "business_id": business_id,
            "total_certifications": len(certifications),
            "active_certifications": len(active_certs),
            "expired_certifications": len(expired_certs),
            "expiring_soon": len(expiring_soon),
            "certifications": decimal_to_float(certifications),
            "compliance_summary": {
                "active": active_certs,
                "expired": expired_certs,
                "expiring_soon": expiring_soon
            }
        })
    except Exception as e:
        return error_response(str(e))

def get_payroll(arguments):
    """Get staff member's payroll history and payment records"""
    try:
        staff_id = arguments['staff_id']
        business_id = arguments.get('business_id')
        limit = arguments.get('limit', 10)
        
        table = dynamodb.Table(PAYROLL_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('staff_id').eq(staff_id),
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        payroll_records = response.get('Items', [])
        
        # Filter by business if provided
        if business_id:
            payroll_records = [p for p in payroll_records if p.get('business_id') == business_id]
        
        # Calculate totals
        total_gross_pay = sum(float(p.get('gross_pay', 0)) for p in payroll_records)
        total_net_pay = sum(float(p.get('net_pay', 0)) for p in payroll_records)
        total_hours = sum(float(p.get('hours_worked', 0)) for p in payroll_records)
        
        return success_response({
            "success": True,
            "staff_id": staff_id,
            "business_id": business_id,
            "records_returned": len(payroll_records),
            "payroll_records": decimal_to_float(payroll_records),
            "summary": {
                "total_gross_pay": total_gross_pay,
                "total_net_pay": total_net_pay,
                "total_hours_worked": total_hours,
                "average_hourly_rate": total_gross_pay / total_hours if total_hours > 0 else 0
            }
        })
    except Exception as e:
        return error_response(str(e))

def get_training(arguments):
    """Get staff member's training history and course completions"""
    try:
        staff_id = arguments['staff_id']
        business_id = arguments.get('business_id')
        
        table = dynamodb.Table(TRAINING_TABLE)
        
        response = table.query(
            KeyConditionExpression=Key('staff_id').eq(staff_id),
            ScanIndexForward=False  # Most recent first
        )
        
        training_records = response.get('Items', [])
        
        # Filter by business if provided
        if business_id:
            training_records = [t for t in training_records if t.get('business_id') == business_id]
        
        # Categorize training
        completed_training = [t for t in training_records if t.get('status') == 'completed']
        in_progress_training = [t for t in training_records if t.get('status') == 'in_progress']
        pending_training = [t for t in training_records if t.get('status') == 'pending']
        
        # Group by training type
        training_by_type = {}
        for training in training_records:
            training_type = training.get('training_type', 'general')
            if training_type not in training_by_type:
                training_by_type[training_type] = []
            training_by_type[training_type].append(training)
        
        return success_response({
            "success": True,
            "staff_id": staff_id,
            "business_id": business_id,
            "total_training_records": len(training_records),
            "completed_courses": len(completed_training),
            "in_progress_courses": len(in_progress_training),
            "pending_courses": len(pending_training),
            "training_records": decimal_to_float(training_records),
            "training_by_type": decimal_to_float(training_by_type),
            "training_summary": {
                "completed": completed_training,
                "in_progress": in_progress_training,
                "pending": pending_training
            }
        })
    except Exception as e:
        return error_response(str(e))
