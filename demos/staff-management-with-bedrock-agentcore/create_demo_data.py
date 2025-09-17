#!/usr/bin/env python3
"""
Create demo data for StaffCast DynamoDB tables.
This script populates the database with sample data for testing.
"""

import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DynamoDB configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
STAFF_TABLE = os.getenv("STAFF_TABLE_NAME", "staffcast-staff")
ROSTER_TABLE = os.getenv("ROSTER_TABLE_NAME", "staffcast-rosters")
AVAILABILITY_TABLE = os.getenv("AVAILABILITY_TABLE_NAME", "staffcast-availability")
BUSINESS_TABLE = os.getenv("BUSINESS_TABLE_NAME", "staffcast-businesses")
HOLIDAYS_TABLE = os.getenv("HOLIDAYS_TABLE_NAME", "staffcast-holidays")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

def create_business_data():
    """Create sample business"""
    table = dynamodb.Table(BUSINESS_TABLE)
    
    business = {
        'business_id': 'cafe-001',
        'name': 'The Daily Grind Cafe',
        'type': 'cafe',
        'address': '123 Main St, Sydney NSW',
        'phone': '02 9876 5432',
        'email': 'info@dailygrind.com',
        'operating_hours': {
            'monday': {'open': '06:00', 'close': '18:00'},
            'tuesday': {'open': '06:00', 'close': '18:00'},
            'wednesday': {'open': '06:00', 'close': '18:00'},
            'thursday': {'open': '06:00', 'close': '20:00'},
            'friday': {'open': '06:00', 'close': '20:00'},
            'saturday': {'open': '07:00', 'close': '17:00'},
            'sunday': {'open': '08:00', 'close': '16:00'}
        },
        'settings': {
            'min_shift_length': Decimal('4'),  # hours
            'max_shift_length': Decimal('10'),  # hours
            'break_after': Decimal('5'),  # hours
            'break_duration': Decimal('30'),  # minutes
            'overtime_threshold': Decimal('38'),  # hours per week
            'overtime_multiplier': Decimal('1.5')
        },
        'positions': [
            {'code': 'manager', 'name': 'Manager', 'color': '#8B5CF6'},
            {'code': 'barista', 'name': 'Barista', 'color': '#3B82F6'},
            {'code': 'chef', 'name': 'Chef', 'color': '#10B981'},
            {'code': 'kitchen_hand', 'name': 'Kitchen Hand', 'color': '#F59E0B'}
        ],
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    table.put_item(Item=business)
    print(f"✓ Created business: {business['name']}")
    return business['business_id']

def create_staff_data(business_id):
    """Create sample staff members"""
    table = dynamodb.Table(STAFF_TABLE)
    
    staff_members = [
        {
            'business_id': business_id,
            'staff_id': 'SM001',
            'name': 'Sarah Mitchell',
            'position': 'manager',
            'email': 'sarah@dailygrind.com',
            'phone': '0412345678',
            'experience_level': 'senior',
            'hourly_rate': Decimal('35.0'),
            'skills': ['management', 'barista', 'inventory', 'training', 'scheduling'],
            'preferred_hours': Decimal('40'),
            'shifts_available': ['morning', 'afternoon'],
            'hire_date': '2020-03-15',
            'emergency_contact': {
                'name': 'John Mitchell',
                'phone': '0412345679',
                'relationship': 'spouse'
            },
            'certifications': [
                {'name': 'Food Safety Certificate', 'expiry_date': '2025-03-15'},
                {'name': 'First Aid Certificate', 'expiry_date': '2024-11-20'},
                {'name': 'RSA Certificate', 'expiry_date': '2025-08-10'}
            ],
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Excellent leader, handles scheduling and training',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'JD002',
            'name': 'James Davidson',
            'position': 'barista',
            'email': 'james@dailygrind.com',
            'phone': '0423456789',
            'experience_level': 'senior',
            'hourly_rate': Decimal('28.0'),
            'skills': ['barista', 'latte_art', 'customer_service', 'training', 'coffee_roasting'],
            'preferred_hours': Decimal('38'),
            'shifts_available': ['morning', 'afternoon'],
            'hire_date': '2021-06-01',
            'emergency_contact': {
                'name': 'Emily Davidson',
                'phone': '0423456790',
                'relationship': 'sister'
            },
            'certifications': [
                {'name': 'SCA Barista Skills', 'expiry_date': '2025-06-01'}
            ],
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Expert in specialty coffee, trains new baristas',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'emma_davis',  # Demo staff ID for staff portal
            'name': 'Emma Davis',
            'position': 'barista',
            'email': 'emma.davis@dailygrind.com',
            'phone': '0434567890',
            'experience_level': 'intermediate',
            'hourly_rate': Decimal('26.5'),
            'skills': ['barista', 'customer_service', 'cash_handling', 'inventory', 'latte_art'],
            'preferred_hours': Decimal('32'),
            'shifts_available': ['morning', 'afternoon', 'evening'],
            'hire_date': '2023-02-15',
            'emergency_contact': {
                'name': 'Michael Davis',
                'phone': '0434567891',
                'relationship': 'brother'
            },
            'certifications': [
                {'name': 'Food Safety Certificate', 'expiry_date': '2025-02-15'},
                {'name': 'Barista Fundamentals', 'expiry_date': '2025-08-15'},
                {'name': 'Customer Service Excellence', 'expiry_date': '2024-12-15'}
            ],
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Reliable team member, excellent with customers, interested in coffee education',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'EC003',
            'name': 'Emma Chen',
            'position': 'barista',
            'email': 'emma@dailygrind.com',
            'phone': '0445678901',
            'experience_level': 'intermediate',
            'hourly_rate': Decimal('25.0'),
            'skills': ['barista', 'customer_service', 'cash_handling', 'inventory'],
            'preferred_hours': Decimal('30'),
            'shifts_available': ['morning', 'afternoon'],
            'hire_date': '2022-09-10',
            'emergency_contact': {
                'name': 'Li Chen',
                'phone': '0445678902',
                'relationship': 'mother'
            },
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Studying part-time, prefers morning shifts on weekends',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'MW004',
            'name': 'Michael Wong',
            'position': 'chef',
            'email': 'michael@dailygrind.com',
            'phone': '0445678901',
            'experience_level': 'senior',
            'hourly_rate': Decimal('32.0'),
            'skills': ['cooking', 'menu_planning', 'food_safety', 'inventory', 'cost_control'],
            'preferred_hours': Decimal('40'),
            'shifts_available': ['morning', 'afternoon'],
            'hire_date': '2019-11-20',
            'emergency_contact': {
                'name': 'Jenny Wong',
                'phone': '0445678902',
                'relationship': 'wife'
            },
            'certifications': [
                {'name': 'Certificate IV in Commercial Cookery', 'expiry_date': '2026-12-31'},
                {'name': 'Food Safety Supervisor Certificate', 'expiry_date': '2025-06-30'}
            ],
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Head chef, manages kitchen operations and menu development',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'LT005',
            'name': 'Lucy Taylor',
            'position': 'barista',
            'email': 'lucy@dailygrind.com',
            'phone': '0456789012',
            'experience_level': 'junior',
            'hourly_rate': Decimal('23.0'),
            'skills': ['barista', 'customer_service'],
            'preferred_hours': Decimal('25'),
            'shifts_available': ['afternoon', 'evening'],
            'hire_date': '2023-04-15',
            'emergency_contact': {
                'name': 'Mark Taylor',
                'phone': '0456789013',
                'relationship': 'father'
            },
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'University student, not available weekends during semester',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'RG006',
            'name': 'Robert Garcia',
            'position': 'chef',
            'email': 'robert@dailygrind.com',
            'phone': '0467890123',
            'experience_level': 'intermediate',
            'hourly_rate': Decimal('28.0'),
            'skills': ['cooking', 'food_safety', 'prep_work', 'grill_station'],
            'preferred_hours': Decimal('35'),
            'shifts_available': ['morning', 'afternoon', 'evening'],
            'hire_date': '2022-02-28',
            'emergency_contact': {
                'name': 'Maria Garcia',
                'phone': '0467890124',
                'relationship': 'sister'
            },
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Reliable kitchen staff, specializes in breakfast menu',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'AP007',
            'name': 'Alex Park',
            'position': 'kitchen_hand',
            'email': 'alex@dailygrind.com',
            'phone': '0478901234',
            'experience_level': 'junior',
            'hourly_rate': Decimal('22.0'),
            'skills': ['dishwashing', 'prep_work', 'cleaning', 'stock_rotation'],
            'preferred_hours': Decimal('30'),
            'shifts_available': ['afternoon', 'evening', 'weekend'],
            'hire_date': '2023-07-20',
            'emergency_contact': {
                'name': 'Jin Park',
                'phone': '0478901235',
                'relationship': 'brother'
            },
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Part-time, very flexible with shifts',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        },
        {
            'business_id': business_id,
            'staff_id': 'NB008',
            'name': 'Nina Brown',
            'position': 'barista',
            'email': 'nina@dailygrind.com',
            'phone': '0489012345',
            'experience_level': 'intermediate',
            'hourly_rate': Decimal('26.0'),
            'skills': ['barista', 'customer_service', 'pos_systems', 'social_media'],
            'preferred_hours': Decimal('35'),
            'shifts_available': ['morning', 'afternoon', 'weekend'],
            'hire_date': '2022-05-15',
            'emergency_contact': {
                'name': 'Tom Brown',
                'phone': '0489012346',
                'relationship': 'partner'
            },
            'is_active': 'true',  # String for GSI compatibility
            'notes': 'Handles social media posts, great with regular customers',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
    ]
    
    for staff in staff_members:
        table.put_item(Item=staff)
        print(f"✓ Created staff member: {staff['name']} ({staff['position']})")
    
    return [s['staff_id'] for s in staff_members]

def create_availability_data(business_id, staff_ids):
    """Create availability for the next 14 days"""
    table = dynamodb.Table(AVAILABILITY_TABLE)
    today = datetime.now()
    
    for i in range(14):
        date = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        day_of_week = (today + timedelta(days=i)).weekday()
        
        for staff_id in staff_ids:
            # Default availability
            available = True
            start_time = "06:00"
            end_time = "22:00"
            notes = None
            
            # Staff-specific availability patterns
            if day_of_week >= 5:  # Weekend
                if staff_id == 'LT005':  # Lucy - uni student
                    available = False
                    notes = "Not available on weekends - university commitments"
                elif staff_id == 'EC003':  # Emma Chen - part-time student
                    end_time = "14:00"
                    notes = "Morning shift only on weekends"
                elif staff_id == 'emma_davis':  # Emma Davis - flexible availability
                    start_time = "08:00"
                    end_time = "18:00"
                    notes = "Available for both morning and afternoon shifts on weekends"
            
            # Emma Davis specific availability patterns
            if staff_id == 'emma_davis':
                if day_of_week < 5:  # Weekdays
                    if day_of_week in [1, 3]:  # Tuesday, Thursday - shorter shifts
                        end_time = "15:00"
                        notes = "Prefers shorter shifts on Tue/Thu"
                    elif day_of_week == 4:  # Friday - longer availability
                        end_time = "20:00"
                        notes = "Available for evening shift on Friday"
            
            # Specific time preferences
            if staff_id in ['SM001', 'JD002', 'MW004']:  # Morning preference
                if available:
                    end_time = "16:00"
            elif staff_id in ['LT005', 'AP007']:  # Afternoon/evening preference
                if available:
                    start_time = "14:00"
            
            item = {
                'staff_id': f"{business_id}#{staff_id}",
                'date': date,
                'business_id': business_id,
                'available': 'true' if available else 'false',  # String for GSI compatibility
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if available:
                item['start_time'] = start_time
                item['end_time'] = end_time
            
            if notes:
                item['notes'] = notes
            
            table.put_item(Item=item)
    
    print(f"✓ Created availability for {len(staff_ids)} staff members for 14 days")

def create_holiday_data(business_id):
    """Create some holiday requests"""
    table = dynamodb.Table(HOLIDAYS_TABLE)
    today = datetime.now()
    
    holidays = [
        {
            'staff_id': f"{business_id}#SM001",
            'holiday_id': 'HOL001',
            'business_id': business_id,
            'start_date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
            'end_date': (today + timedelta(days=16)).strftime('%Y-%m-%d'),
            'days': Decimal('3'),
            'type': 'annual_leave',
            'reason': 'Long weekend trip to Melbourne',
            'status': 'approved',
            'requested_at': (today - timedelta(days=30)).isoformat(),
            'approved_at': (today - timedelta(days=28)).isoformat(),
            'approved_by': 'owner',
            'updated_at': (today - timedelta(days=28)).isoformat()
        },
        {
            'staff_id': f"{business_id}#JD002",
            'holiday_id': 'HOL002',
            'business_id': business_id,
            'start_date': (today + timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': (today + timedelta(days=37)).strftime('%Y-%m-%d'),
            'days': Decimal('8'),
            'type': 'annual_leave',
            'reason': 'Family vacation to Bali',
            'status': 'pending',
            'requested_at': (today - timedelta(days=5)).isoformat(),
            'updated_at': (today - timedelta(days=5)).isoformat()
        },
        {
            'staff_id': f"{business_id}#emma_davis",
            'holiday_id': 'HOL003',
            'business_id': business_id,
            'start_date': (today + timedelta(days=10)).strftime('%Y-%m-%d'),
            'end_date': (today + timedelta(days=12)).strftime('%Y-%m-%d'),
            'days': Decimal('3'),
            'type': 'annual_leave',
            'reason': 'Weekend getaway with friends',
            'status': 'pending',
            'requested_at': (today - timedelta(days=2)).isoformat(),
            'updated_at': (today - timedelta(days=2)).isoformat()
        },
        {
            'staff_id': f"{business_id}#emma_davis",
            'holiday_id': 'HOL004',
            'business_id': business_id,
            'start_date': (today + timedelta(days=25)).strftime('%Y-%m-%d'),
            'end_date': (today + timedelta(days=25)).strftime('%Y-%m-%d'),
            'days': Decimal('1'),
            'type': 'personal_leave',
            'reason': 'Medical appointment',
            'status': 'approved',
            'requested_at': (today - timedelta(days=10)).isoformat(),
            'approved_at': (today - timedelta(days=8)).isoformat(),
            'approved_by': 'SM001',
            'updated_at': (today - timedelta(days=8)).isoformat()
        },
        {
            'staff_id': f"{business_id}#MW004",
            'holiday_id': 'HOL005',
            'business_id': business_id,
            'start_date': (today - timedelta(days=7)).strftime('%Y-%m-%d'),
            'end_date': (today - timedelta(days=5)).strftime('%Y-%m-%d'),
            'days': Decimal('3'),
            'type': 'sick_leave',
            'reason': 'Medical certificate provided',
            'status': 'approved',
            'requested_at': (today - timedelta(days=8)).isoformat(),
            'approved_at': (today - timedelta(days=8)).isoformat(),
            'approved_by': 'SM001',
            'updated_at': (today - timedelta(days=8)).isoformat()
        }
    ]
    
    for holiday in holidays:
        table.put_item(Item=holiday)
        print(f"✓ Created holiday request: {holiday['holiday_id']} - {holiday['reason']}")

def create_sample_roster(business_id):
    """Create a sample roster for tomorrow"""
    table = dynamodb.Table(ROSTER_TABLE)
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    shifts = [
        {
            'staff_id': 'SM001',
            'staff_name': 'Sarah Mitchell',
            'position': 'manager',
            'start_time': '08:00',
            'end_time': '16:00',
            'break_duration': Decimal('30'),
            'hourly_rate': Decimal('35.0'),
            'hours': Decimal('7.5'),
            'cost': Decimal('262.5')
        },
        {
            'staff_id': 'JD002',
            'staff_name': 'James Davidson',
            'position': 'barista',
            'start_time': '06:00',
            'end_time': '14:00',
            'break_duration': Decimal('30'),
            'hourly_rate': Decimal('28.0'),
            'hours': Decimal('7.5'),
            'cost': Decimal('210.0')
        },
        {
            'staff_id': 'EC003',
            'staff_name': 'Emma Chen',
            'position': 'barista',
            'start_time': '11:00',
            'end_time': '19:00',
            'break_duration': Decimal('30'),
            'hourly_rate': Decimal('25.0'),
            'hours': Decimal('7.5'),
            'cost': Decimal('187.5')
        },
        {
            'staff_id': 'MW004',
            'staff_name': 'Michael Wong',
            'position': 'chef',
            'start_time': '06:00',
            'end_time': '14:00',
            'break_duration': Decimal('30'),
            'hourly_rate': Decimal('32.0'),
            'hours': Decimal('7.5'),
            'cost': Decimal('240.0')
        },
        {
            'staff_id': 'AP007',
            'staff_name': 'Alex Park',
            'position': 'kitchen_hand',
            'start_time': '12:00',
            'end_time': '20:00',
            'break_duration': Decimal('30'),
            'hourly_rate': Decimal('22.0'),
            'hours': Decimal('7.5'),
            'cost': Decimal('165.0')
        }
    ]
    
    roster = {
        'business_id': business_id,
        'roster_date': tomorrow,
        'shifts': shifts,
        'status': 'published',
        'total_hours': Decimal('37.5'),
        'total_cost': Decimal('1065.0'),
        'notes': 'Standard weekday roster',
        'weather_forecast': {
            'condition': 'partly_cloudy',
            'temperature': Decimal('22'),
            'precipitation': Decimal('0')
        },
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'published_at': datetime.utcnow().isoformat(),
        'published_by': 'SM001'
    }
    
    table.put_item(Item=roster)
    print(f"✓ Created sample roster for {tomorrow}")

def main():
    print("🚀 Creating demo data for StaffCast...")
    print("=" * 50)
    
    try:
        # Create business
        business_id = create_business_data()
        
        # Create staff
        staff_ids = create_staff_data(business_id)
        
        # Create availability
        create_availability_data(business_id, staff_ids)
        
        # Create holidays
        create_holiday_data(business_id)
        
        # Create sample roster
        create_sample_roster(business_id)
        
        print("\n✅ Demo data created successfully!")
        print(f"\nBusiness ID: {business_id}")
        print(f"Staff created: {len(staff_ids)}")
        print("\nYou can now test the StaffCast system with this data.")
        
    except Exception as e:
        print(f"\n❌ Error creating demo data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()