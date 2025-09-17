"""
Generate and upload company policy documents to S3 and populate new database tables
Infrastructure is managed by CloudFormation
"""

import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("POLICY_BUCKET_NAME", "")  # From CloudFormation output
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")  # From CloudFormation output

# New table names from CloudFormation
CERTIFICATIONS_TABLE = os.getenv("CERTIFICATIONS_TABLE_NAME", "staffcast-dev-certifications")
PAYROLL_TABLE = os.getenv("PAYROLL_TABLE_NAME", "staffcast-dev-payroll") 
TRAINING_TABLE = os.getenv("TRAINING_TABLE_NAME", "staffcast-dev-training")

# Demo staff configuration
DEMO_STAFF_ID = os.getenv("DEMO_STAFF_ID", "emma_davis")
DEMO_BUSINESS_ID = os.getenv("DEMO_BUSINESS_ID", "cafe-001")

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_REGION)
bedrock_agent = boto3.client('bedrock-agent', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# Sample company policies for The Daily Grind Cafe
SAMPLE_POLICIES = {
    "leave_policy.md": """# Leave and Holiday Policy

## Annual Leave Entitlement
- Full-time employees: 20 days per year
- Part-time employees: Pro-rata based on hours worked
- Casual employees: No annual leave entitlement

## Requesting Leave
1. Submit leave request at least 2 weeks in advance
2. Use StaffCast system to submit requests
3. Manager approval required for all leave
4. Emergency leave may be approved with less notice

## Public Holidays
- All permanent staff receive public holiday rates (1.5x normal rate)
- Casual staff receive loading on public holidays
- Voluntary work on public holidays

## Sick Leave
- 10 days per year for full-time employees
- Accumulates up to 30 days
- Medical certificate required for 2+ consecutive days
- Notify manager before shift start time

## Compassionate Leave
- 3 days paid leave for immediate family
- Additional unpaid leave may be granted
- Documentation may be required
""",

    "payroll_policy.md": """# Payroll and Compensation Policy

## Pay Periods
- Fortnightly pay cycle
- Pay day: Every second Thursday
- Pay period: Monday to Sunday

## Hourly Rates
- Base rates as per employment agreement
- Weekend rates: Saturday 1.25x, Sunday 1.5x
- Public holidays: 2.5x base rate
- Night shift (after 10pm): Additional $2/hour

## Overtime
- Overtime applies after 38 hours/week (full-time)
- Time and a half for first 2 hours
- Double time thereafter
- All overtime must be pre-approved

## Superannuation
- 11.5% of ordinary earnings
- Paid quarterly
- Choice of fund available
- Salary sacrifice options available

## Payslips
- Available via employee portal
- Includes YTD totals
- Leave balances shown
- Tax and super details included
""",

    "safety_procedures.md": """# Workplace Health and Safety Procedures

## General Safety Rules
1. Report all hazards immediately
2. Use proper lifting techniques
3. Wear non-slip shoes at all times
4. Keep work areas clean and organized

## Kitchen Safety
- Always use oven mitts for hot items
- Sharp knives stored in designated areas
- Report damaged equipment immediately
- Follow HACCP procedures for food safety

## Emergency Procedures
- Fire exits clearly marked
- Assembly point: Front car park
- First aid kit located behind counter
- Emergency numbers posted by phone

## Incident Reporting
1. Notify manager immediately
2. Complete incident report within 24 hours
3. Seek medical attention if required
4. WorkCover claims if applicable

## COVID-19 Safety
- Stay home if unwell
- Regular hand washing required
- Sanitizer stations available
- Masks optional but supported
""",

    "training_requirements.md": """# Training and Certification Requirements

## Mandatory Training
All staff must complete:
1. Food Safety Level 1 (within first week)
2. Responsible Service of Alcohol (if applicable)
3. Coffee Making Basics (baristas)
4. WHS Induction (first day)

## Ongoing Training
- Annual food safety refresher
- New equipment training as needed
- Customer service workshops quarterly
- Leadership training for supervisors

## Certifications
Required certifications by position:
- Barista: Coffee making certificate
- Chef: Food Safety Supervisor certificate
- Manager: First Aid certificate
- All: Working with Children Check (if under 18 on premises)

## Training Records
- All training recorded in staff file
- Certificates uploaded to system
- Reminders sent for expiring certifications
- Training costs covered by employer

## Professional Development
- Study leave available for relevant courses
- Partial reimbursement for approved training
- Internal mentoring program available
- Cross-training opportunities
""",

    "code_of_conduct.md": """# Employee Code of Conduct

## Professional Behavior
- Treat all colleagues with respect
- No discrimination or harassment
- Maintain professional appearance
- Punctuality is essential

## Customer Service Standards
- Greet all customers warmly
- Address complaints professionally
- Maintain confidentiality
- Go above and beyond when possible

## Social Media Policy
- No negative comments about workplace
- Don't share confidential information
- Personal accounts are your responsibility
- Official accounts managed by marketing only

## Uniform and Appearance
- Clean uniform required daily
- Name badge must be worn
- Hair tied back in food areas
- Minimal jewelry for safety

## Disciplinary Process
1. Verbal warning
2. Written warning
3. Final warning
4. Termination
Note: Serious misconduct may result in immediate termination
""",

    "benefits_overview.md": """# Employee Benefits Overview

## Health and Wellbeing
- Employee Assistance Program (EAP) - free counseling
- Discounted gym membership
- Annual flu vaccination
- Mental health days (2 per year)

## Financial Benefits
- Staff discount: 30% on all food and beverages
- Salary packaging options
- Performance bonuses (quarterly)
- Long service leave

## Work-Life Balance
- Flexible scheduling where possible
- Job sharing opportunities
- Unpaid career breaks available
- Study leave for relevant courses

## Recognition Programs
- Employee of the Month
- Service awards (yearly milestones)
- Team building events
- Christmas party and bonuses

## Career Development
- Internal promotion preference
- Skills training provided
- Mentorship programs
- Conference attendance support
""",

    "rostering_guidelines.md": """# Rostering and Scheduling Guidelines

## Scheduling Principles
- Fair distribution of shifts
- Consider staff availability and preferences
- Ensure adequate coverage for all periods
- Balance experience levels across shifts

## Shift Requirements
- Minimum 2 baristas during peak hours (7am-10am, 12pm-2pm)
- At least 1 supervisor per shift
- Kitchen staff required for food service hours
- Minimum 3 hours per shift

## Availability Management
- Update availability 2 weeks in advance
- Permanent changes require manager approval
- Temporary unavailability must be reported ASAP
- Holiday requests processed in order received

## Shift Swapping
- Staff may arrange shift swaps with approval
- Both parties must agree in writing
- Manager notification required 24 hours prior
- Similar skill levels preferred

## Emergency Coverage
- On-call list maintained for urgent coverage
- Casual staff may be contacted for extra shifts
- Overtime rates apply for emergency calls
- Staff appreciation for flexibility
"""
}

def upload_policies_to_s3():
    """Upload sample policy documents to S3"""
    if not BUCKET_NAME:
        print("❌ Error: POLICY_BUCKET_NAME not set in environment")
        print("Please set it from the CloudFormation stack outputs")
        return False
    
    print(f"📤 Uploading policies to S3 bucket: {BUCKET_NAME}")
    
    success_count = 0
    for filename, content in SAMPLE_POLICIES.items():
        try:
            # Upload with metadata for better organization
            category = filename.split('_')[0]
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=f"policies/{filename}",
                Body=content.encode('utf-8'),
                ContentType='text/markdown',
                Metadata={
                    'category': category,
                    'company': 'The Daily Grind Cafe',
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0'
                }
            )
            print(f"  ✓ Uploaded {filename} (category: {category})")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed to upload {filename}: {e}")
    
    print(f"\n📊 Upload Summary: {success_count}/{len(SAMPLE_POLICIES)} files uploaded successfully")
    return success_count == len(SAMPLE_POLICIES)

def trigger_knowledge_base_sync():
    """Trigger the Knowledge Base to sync new documents"""
    if not KNOWLEDGE_BASE_ID:
        print("⚠️  KNOWLEDGE_BASE_ID not set - skipping sync")
        print("Set KNOWLEDGE_BASE_ID from CloudFormation outputs and run sync manually")
        return False
    
    try:
        print(f"🔄 Triggering Knowledge Base sync: {KNOWLEDGE_BASE_ID}")
        
        # List data sources for the knowledge base
        data_sources = bedrock_agent.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        if not data_sources.get('dataSourceSummaries'):
            print("  ⚠️  No data sources found for this Knowledge Base")
            return False
        
        # Start ingestion job for the first data source
        data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id,
            description=f"Policy documents sync - {datetime.now().isoformat()}"
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        print(f"  ✓ Started ingestion job: {ingestion_job_id}")
        print(f"  ⏳ Documents will be available for search in a few minutes")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to sync Knowledge Base: {e}")
        return False

def populate_certifications_table():
    """Populate certifications table with sample data"""
    print("\n📜 Populating Certifications table...")
    
    try:
        table = dynamodb.Table(CERTIFICATIONS_TABLE)
        
        # Sample certifications for our demo staff
        certifications = [
            # Emma Davis (demo staff member)
            {
                'staff_id': DEMO_STAFF_ID,
                'certification_id': 'food_safety_001',
                'business_id': DEMO_BUSINESS_ID,
                'certification_type': 'food_safety',
                'certification_name': 'Food Safety Level 1',
                'issued_date': '2024-01-15',
                'expiry_date': '2026-01-15',
                'issuing_authority': 'Food Safety Australia',
                'status': 'active',
                'certificate_url': 's3://certificates/emma_food_safety.pdf'
            },
            {
                'staff_id': DEMO_STAFF_ID, 
                'certification_id': 'barista_001',
                'business_id': DEMO_BUSINESS_ID,
                'certification_type': 'barista',
                'certification_name': 'Professional Barista Certificate',
                'issued_date': '2023-11-20',
                'expiry_date': '2025-11-20',
                'issuing_authority': 'Coffee Institute of Australia',
                'status': 'active',
                'certificate_url': 's3://certificates/emma_barista.pdf'
            },
            # Sarah Johnson (Manager)
            {
                'staff_id': 'sarah_johnson',
                'certification_id': 'first_aid_001', 
                'business_id': DEMO_BUSINESS_ID,
                'certification_type': 'first_aid',
                'certification_name': 'Senior First Aid Certificate',
                'issued_date': '2024-03-10',
                'expiry_date': '2027-03-10',
                'issuing_authority': 'Red Cross Australia',
                'status': 'active',
                'certificate_url': 's3://certificates/sarah_first_aid.pdf'
            },
            {
                'staff_id': 'sarah_johnson',
                'certification_id': 'food_supervisor_001',
                'business_id': DEMO_BUSINESS_ID, 
                'certification_type': 'food_safety',
                'certification_name': 'Food Safety Supervisor Certificate',
                'issued_date': '2023-12-01',
                'expiry_date': '2028-12-01',
                'issuing_authority': 'Food Safety Australia',
                'status': 'active',
                'certificate_url': 's3://certificates/sarah_food_supervisor.pdf'
            }
        ]
        
        for cert in certifications:
            table.put_item(Item=cert)
            print(f"  ✓ Added certification: {cert['certification_name']} for {cert['staff_id']}")
        
        print(f"  📊 Total certifications added: {len(certifications)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to populate certifications: {e}")
        return False

def populate_payroll_table():
    """Populate payroll table with sample data"""
    print("\n💰 Populating Payroll table...")
    
    try:
        table = dynamodb.Table(PAYROLL_TABLE)
        
        # Generate payroll records for the past 3 months
        payroll_records = []
        base_date = datetime(2025, 6, 1)  # Start from June 2025
        
        # Staff payroll data
        staff_rates = {
            DEMO_STAFF_ID: {'hourly_rate': Decimal('18.00'), 'position': 'Barista'},
            'sarah_johnson': {'hourly_rate': Decimal('25.00'), 'position': 'Manager'},
            'james_wilson': {'hourly_rate': Decimal('20.00'), 'position': 'Barista'},
            'michael_brown': {'hourly_rate': Decimal('22.00'), 'position': 'Chef'}
        }
        
        for month_offset in range(3):  # 3 months of data
            pay_period_start = base_date + timedelta(days=month_offset * 30)
            pay_period_end = pay_period_start + timedelta(days=13)  # Fortnightly
            pay_period = pay_period_start.strftime('%Y-%m-%d')
            payment_date = (pay_period_end + timedelta(days=3)).strftime('%Y-%m-%d')
            
            for staff_id, rates in staff_rates.items():
                # Calculate sample pay
                regular_hours = Decimal('76')  # Standard fortnight
                overtime_hours = Decimal('4') if staff_id == 'sarah_johnson' else Decimal('0')
                
                regular_pay = regular_hours * rates['hourly_rate']
                overtime_pay = overtime_hours * rates['hourly_rate'] * Decimal('1.5')
                gross_pay = regular_pay + overtime_pay
                tax = gross_pay * Decimal('0.25')  # Sample tax
                super_contribution = gross_pay * Decimal('0.115')  # 11.5% super
                net_pay = gross_pay - tax
                
                payroll_record = {
                    'staff_id': staff_id,
                    'pay_period': pay_period,
                    'business_id': DEMO_BUSINESS_ID,
                    'payment_date': payment_date,
                    'regular_hours': regular_hours,
                    'overtime_hours': overtime_hours,
                    'hourly_rate': rates['hourly_rate'],
                    'regular_pay': regular_pay,
                    'overtime_pay': overtime_pay,
                    'gross_pay': gross_pay,
                    'tax_withheld': tax,
                    'superannuation': super_contribution,
                    'net_pay': net_pay,
                    'position': rates['position'],
                    'pay_type': 'regular',
                    'status': 'paid'
                }
                
                payroll_records.append(payroll_record)
        
        # Insert records
        for record in payroll_records:
            table.put_item(Item=record)
            print(f"  ✓ Added payroll record: {record['staff_id']} - {record['pay_period']} (${float(record['net_pay']):.2f})")
        
        print(f"  📊 Total payroll records added: {len(payroll_records)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to populate payroll: {e}")
        return False

def populate_training_table():
    """Populate training table with sample data"""
    print("\n🎓 Populating Training table...")
    
    try:
        table = dynamodb.Table(TRAINING_TABLE)
        
        # Sample training records
        training_records = [
            # Emma Davis training
            {
                'staff_id': DEMO_STAFF_ID,
                'training_id': 'whs_induction_001',
                'business_id': DEMO_BUSINESS_ID,
                'training_type': 'safety',
                'training_name': 'Workplace Health & Safety Induction',
                'completion_date': '2023-10-01',
                'trainer': 'Sarah Johnson',
                'duration_hours': Decimal('2'),
                'status': 'completed',
                'score': Decimal('95'),
                'certificate_issued': True,
                'next_due_date': '2024-10-01'
            },
            {
                'staff_id': DEMO_STAFF_ID,
                'training_id': 'customer_service_001',
                'business_id': DEMO_BUSINESS_ID, 
                'training_type': 'customer_service',
                'training_name': 'Customer Service Excellence',
                'completion_date': '2024-02-15',
                'trainer': 'External Provider',
                'duration_hours': Decimal('4'),
                'status': 'completed',
                'score': Decimal('88'),
                'certificate_issued': True,
                'next_due_date': '2025-02-15'
            },
            {
                'staff_id': DEMO_STAFF_ID,
                'training_id': 'coffee_advanced_001',
                'business_id': DEMO_BUSINESS_ID,
                'training_type': 'technical',
                'training_name': 'Advanced Latte Art Techniques',
                'completion_date': '2024-05-20',
                'trainer': 'James Wilson',
                'duration_hours': Decimal('6'),
                'status': 'completed',
                'score': Decimal('92'),
                'certificate_issued': True,
                'next_due_date': None  # No renewal required
            },
            # Sarah Johnson training
            {
                'staff_id': 'sarah_johnson',
                'training_id': 'leadership_001',
                'business_id': DEMO_BUSINESS_ID,
                'training_type': 'leadership',
                'training_name': 'Team Leadership & Management',
                'completion_date': '2024-01-10',
                'trainer': 'External Provider',
                'duration_hours': Decimal('16'),
                'status': 'completed',
                'score': Decimal('97'),
                'certificate_issued': True,
                'next_due_date': '2027-01-10'
            }
        ]
        
        for record in training_records:
            table.put_item(Item=record)
            print(f"  ✓ Added training record: {record['training_name']} for {record['staff_id']}")
        
        print(f"  📊 Total training records added: {len(training_records)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to populate training: {e}")
        return False

def main():
    print("📚 StaffCast Extended Data Generator")
    print("=" * 60)
    print("🏗️  Generating data for dual-portal architecture:")
    print("  • Policy documents (Knowledge Base)")
    print("  • Staff certifications")
    print("  • Payroll records") 
    print("  • Training history")
    print("=" * 60)
    
    success_count = 0
    total_tasks = 5
    
    # Upload policies to S3
    if upload_policies_to_s3():
        print("\n✅ Policy documents uploaded successfully!")
        success_count += 1
        
        # Trigger Knowledge Base sync
        print("\n🔄 Attempting to sync Knowledge Base...")
        if trigger_knowledge_base_sync():
            print("\n🎉 Knowledge Base sync initiated!")
            success_count += 1
        else:
            print("\n⚠️  Knowledge Base sync not completed.")
    else:
        print("\n❌ Policy document upload failed.")
    
    # Populate new database tables
    if populate_certifications_table():
        success_count += 1
    
    if populate_payroll_table():
        success_count += 1
        
    if populate_training_table():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 COMPLETION SUMMARY: {success_count}/{total_tasks} tasks completed")
    
    if success_count == total_tasks:
        print("🎉 ALL SYSTEMS READY!")
        print("\n🚀 Staff Portal Features Now Available:")
        print("  • Policy search via Knowledge Base")
        print("  • Certification tracking")
        print("  • Payroll history access")
        print("  • Training record management")
        
        print("\n💡 Staff can now ask questions like:")
        print('  • "What certifications do I have?"')
        print('  • "When was my last pay?"')
        print('  • "What training do I need to complete?"')
        print('  • "What is our leave policy?"')
        print('  • "When does my food safety certificate expire?"')
    else:
        print("⚠️  Some tasks incomplete - check error messages above")
        print("Manual intervention may be required for failed components")
    
    print("\n📋 Next Steps:")
    print("1. Verify CloudFormation stack completed successfully")
    print("2. Test manager API (port 8080)")
    print("3. Test staff API (port 8081)")  
    print("4. Deploy Material UI frontend updates")
    print("5. Test dual-portal functionality")

if __name__ == "__main__":
    main()