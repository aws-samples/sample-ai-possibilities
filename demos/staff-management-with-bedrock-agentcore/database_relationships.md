# StaffCast Database Relationships & Agent Search Patterns

## Table Relationships Overview - Expanded Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│    BUSINESS     │    │      STAFF       │    │    AVAILABILITY     │
│                 │    │                  │    │                     │
│ PK: business_id │◄───┤ PK: business_id  │    │ PK: staff_id        │
│                 │    │     staff_id     │◄───┤     (bus_id#staff)  │
│ - name          │    │                  │    │ SK: date            │
│ - type          │    │ - name           │    │                     │
│ - hours         │    │ - position       │    │ - available         │
│ - settings      │    │ - hourly_rate    │    │ - start/end_time    │
└─────────────────┘    │ - experience     │    │ - notes             │
                       │ - skills         │    └─────────────────────┘
                       │ - hire_date      │              │
                       └──────────────────┘              │
                                │                        │
                                │                        │
            ┌───────────────────┼────────────────────────┼──────────────┐
            │                   │                        │              │
            │                   │                        │              │
   ┌──────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
   │   CERTIFICATIONS │  │      HOLIDAYS       │  │      ROSTERS        │  │      PAYROLL        │
   │                  │  │                     │  │                     │  │                     │
   │ PK: staff_id     │  │ PK: staff_id        │  │ PK: business_id     │  │ PK: staff_id        │
   │ SK: cert_id      │  │     (bus_id#staff)  │  │ SK: roster_date     │  │ SK: pay_period      │
   │                  │  │ SK: holiday_id      │  │                     │  │                     │
   │ - cert_name      │  │                     │  │ - shifts[]          │  │ - hours_worked      │
   │ - cert_type      │  │ - start_date        │  │   ├─ staff_id       │  │ - gross_pay         │
   │ - expiry_date    │  │ - end_date          │  │   ├─ position       │  │ - deductions        │
   │ - status         │  │ - type              │  │   └─ times          │  │ - net_pay           │
   │ - business_id    │  │ - status            │  │ - total_cost        │  │ - payment_date      │
   │                  │  │                     │  │ - weather           │  │ - business_id       │
   │ GSI: BusinessIdx │  └─────────────────────┘  └─────────────────────┘  │                     │
   │ GSI: TypeIdx     │                                                    │ GSI: BusinessIdx    │
   └──────────────────┘                                                    └─────────────────────┘
                                        │
                                        │
                               ┌─────────────────────┐
                               │      TRAINING       │
                               │                     │
                               │ PK: staff_id        │
                               │ SK: training_id     │
                               │                     │
                               │ - training_name     │
                               │ - training_type     │
                               │ - completion_date   │
                               │ - status            │
                               │ - business_id       │
                               │                     │
                               │ GSI: BusinessIdx    │
                               │ GSI: TypeIdx        │
                               └─────────────────────┘
```

## Knowledge Base Integration

### AWS Infrastructure
```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────────┐
│    S3 BUCKET        │    │   OPENSEARCH         │    │   BEDROCK KNOWLEDGE     │
│   (Private)         │    │   SERVERLESS         │    │        BASE             │
│                     │    │                      │    │                         │
│ - Policy PDFs       │◄───┤ Vector Collection    │◄───┤ Cohere Embeddings       │
│ - HR Documents      │    │ - Vector Index       │    │ - Query Processing      │
│ - Training Materials│    │ - Encrypted          │    │ - Policy Search         │
│ - Company Procedures│    │ - Private Network    │    │ - AI-Powered Retrieval  │
└─────────────────────┘    └──────────────────────┘    └─────────────────────────┘
```

## New Tables - Staff Extensions

### 1. **Certifications Table**
- **Purpose**: Track staff certifications, licenses, and compliance requirements
- **Key Fields**: `staff_id` (PK), `certification_id` (SK), `expiry_date`, `certification_type`
- **GSIs**: 
  - `BusinessIndex`: Query by business and expiry date (for renewal alerts)
  - `TypeIndex`: Query by certification type and expiry date (compliance reporting)

### 2. **Payroll Table**
- **Purpose**: Store payroll records and payment history
- **Key Fields**: `staff_id` (PK), `pay_period` (SK), `hours_worked`, `gross_pay`, `net_pay`
- **GSIs**: 
  - `BusinessPayrollIndex`: Query by business and payment date (payroll reports)

### 3. **Training Table**
- **Purpose**: Track training completion, courses, and skill development
- **Key Fields**: `staff_id` (PK), `training_id` (SK), `training_type`, `completion_date`
- **GSIs**: 
  - `BusinessTrainingIndex`: Query by business and completion date (training reports)
  - `TrainingTypeIndex`: Query by training type and completion date (skill analysis)

## Dual-Portal Architecture

### Manager Portal Access
- **Full Access**: All tables and operations
- **Tools**: Complete MCP toolset including roster generation, staff management, approvals
- **Data Scope**: Business-wide visibility and control

### Staff Portal Access (Restricted)
- **Limited Access**: Personal data only with filtered responses
- **Tools**: Restricted MCP toolset (view own data, submit requests)
- **Data Scope**: Own records + general business information
- **Knowledge Base**: Full access to company policies via Bedrock Knowledge Base

```
┌─────────────────────┐    ┌─────────────────────┐
│   MANAGER PORTAL    │    │    STAFF PORTAL     │
│                     │    │                     │
│ All Tables:         │    │ Filtered Access:    │
│ ✓ Staff (all)       │    │ ✓ Staff (own only)  │
│ ✓ Rosters (manage)  │    │ ✓ Rosters (view)    │
│ ✓ Holidays (approve)│    │ ✓ Holidays (own)    │
│ ✓ Availability (all)│    │ ✓ Availability (own)│
│ ✓ Certifications    │    │ ✓ Certifications    │
│ ✓ Payroll (all)     │    │ ✓ Payroll (own)     │
│ ✓ Training (all)    │    │ ✓ Training (own)    │
│                     │    │ ✓ Knowledge Base    │
└─────────────────────┘    └─────────────────────┘
```

## Key Relationship Patterns

### 1. **Primary Relationships**
- `business_id` is the main connector across all tables
- `staff_id` format: For cross-table references, some use `business_id#staff_id`
- All tables include `business_id` for efficient business-scoped queries
- New tables follow consistent schema patterns with proper GSI design

### 2. **Current Issues & Improvements Needed**

#### ❌ **Inconsistent Staff ID References**
```python
# CURRENT (Inconsistent):
Staff Table:     staff_id = "SM001"
Availability:    staff_id = "cafe-001#SM001"  
Holidays:        staff_id = "cafe-001#SM001"
Rosters:         shifts[].staff_id = "SM001"

# SHOULD BE (Consistent):
All tables should use either:
Option A: Always "business_id#staff_id" format
Option B: Always separate business_id + staff_id fields
```

#### ❌ **Missing Cross-Reference Fields**
```python
# AVAILABILITY table should include:
{
    'staff_id': 'cafe-001#SM001',
    'date': '2024-01-15',
    'business_id': 'cafe-001',          # ✓ Already present
    'actual_staff_id': 'SM001',         # ❌ Missing - needed for roster matching
    'position': 'barista'               # ❌ Missing - needed for filtering
}

# ROSTER shifts should include:
{
    'staff_id': 'SM001',
    'staff_name': 'Sarah Mitchell',
    'position': 'barista',
    'full_staff_id': 'cafe-001#SM001'   # ❌ Missing - needed for availability lookup
}
```

## Agent Search Patterns & Efficiency

### 1. **Common Agent Queries - Extended**
```python
# "Find all available baristas for tomorrow"
# Current: Requires 3 separate queries
1. get_staff(business_id, position="barista") 
2. get_availability(business_id, date="2024-01-16")
3. Manual matching of results

# "Generate roster suggestions considering holidays"
# Current: Requires 4 separate queries
1. get_staff(business_id)
2. get_availability(business_id, date_range)
3. get_holidays(business_id, date_range)
4. Manual cross-referencing

# NEW: "Find staff with expiring food safety certifications"
# Requires certification table query
1. query_certifications(business_id, cert_type="food_safety", expiry_within=30)
2. get_staff_details for notification

# NEW: "Show Emma's training history and upcoming requirements"
# Staff portal query (filtered to own data)
1. get_training(staff_id="emma_davis") 
2. get_certifications(staff_id="emma_davis")
3. Cross-reference with compliance requirements

# NEW: "Calculate total payroll costs for last quarter"
# Manager portal query with business-wide access
1. get_payroll(business_id, date_range="2024-Q4")
2. Aggregate gross_pay across all staff
```

### 2. **Improved Design for Agent Efficiency**

#### **Enhanced Availability Table**
```python
{
    'staff_id': 'cafe-001#SM001',        # Composite key
    'date': '2024-01-15',                # Sort key
    'business_id': 'cafe-001',           # GSI partition key
    'actual_staff_id': 'SM001',          # Clean staff ID
    'staff_name': 'Sarah Mitchell',      # Denormalized for efficiency
    'position': 'barista',               # Denormalized for filtering
    'experience_level': 'senior',        # Denormalized for roster logic
    'available': True,
    'start_time': '06:00',
    'end_time': '16:00',
    'on_holiday': False,                 # Computed field
    'holiday_type': None,                # If on holiday
    'notes': 'Morning shift preferred'
}
```

#### **Enhanced Roster Table**
```python
{
    'business_id': 'cafe-001',
    'roster_date': '2024-01-15',
    'shifts': [
        {
            'staff_id': 'SM001',
            'full_staff_id': 'cafe-001#SM001',  # For cross-table lookups
            'staff_name': 'Sarah Mitchell',
            'position': 'barista',
            'experience_level': 'senior',
            'start_time': '06:00',
            'end_time': '16:00',
            'hourly_rate': 35.0,
            'was_available': True,              # Historical availability
            'availability_notes': 'Preferred'  # Why chosen
        }
    ]
}
```

### 3. **Global Secondary Index (GSI) Strategy**

#### **Current GSIs**
```python
# Staff Table
- PositionIndex: business_id + position
- ActiveStaffIndex: business_id + is_active

# Availability Table  
- BusinessDateIndex: business_id + date
- AvailabilityIndex: business_id + available

# Could be improved with combined indexes
```

#### **Recommended Additional GSIs**
```python
# For "available staff by position and date"
AvailabilityPositionIndex: business_id + position#date
# Query: All available baristas for specific date

# For "staff experience by availability" 
ExperienceAvailabilityIndex: business_id + experience_level#available
# Query: All senior staff available today
```

## Agent-Friendly Query Functions

### **Proposed Enhanced MCP Tools**

```python
@mcp.tool(description="Get staff with integrated availability and holiday status")
def get_staff_with_status(
    business_id: str,
    date: str,
    position: Optional[str] = None,
    available_only: bool = True,
    include_holiday_info: bool = True
) -> Dict[str, Any]:
    """
    Single query that returns staff with:
    - Basic staff info
    - Availability for specific date  
    - Holiday status
    - Experience and skills
    """

@mcp.tool(description="Get comprehensive roster context")
def get_roster_context(
    business_id: str,
    date: str
) -> Dict[str, Any]:
    """
    Single query returning everything needed for roster generation:
    - All staff with availability
    - Holiday conflicts
    - Existing roster (if any)
    - Business operating hours
    - Weather data (if available)
    """
```

## Recommendations

### 1. **Data Consistency Fixes**
- Standardize staff_id format across all tables (✓ Implemented in new tables)
- Add denormalized fields for common lookups
- Ensure all cross-references use consistent keys
- Maintain business_id isolation for multi-tenant security

### 2. **Agent Efficiency Improvements**
- Create composite query functions for staff portal optimization
- Add computed fields (like `on_holiday` in availability, `expires_soon` in certifications)
- Pre-calculate common agent queries
- Implement staff data filtering at the database query level for security

### 3. **Index Optimization**
- ✓ **Implemented**: GSIs for new tables support business-scoped queries
- ✓ **Certifications**: BusinessIndex and TypeIndex for compliance monitoring
- ✓ **Payroll**: BusinessPayrollIndex for financial reporting
- ✓ **Training**: BusinessTrainingIndex and TypeIndex for skill analysis
- Consider sparse indexes for optional fields
- Use composite sort keys for multi-dimensional queries

### 4. **Knowledge Base Integration**
- ✓ **Implemented**: Private S3 bucket with OpenSearch Serverless
- ✓ **Security**: IAM roles restrict access appropriately
- ✓ **Staff Access**: Native Strands KnowledgeBaseTool integration
- Consider indexing by business_id for multi-tenant policy separation

### 5. **Dual-Portal Security**
- ✓ **Access Control**: Separate IAM roles for manager vs staff access
- ✓ **Data Filtering**: Tool response filtering ensures staff only see own data
- ✓ **Tool Restrictions**: Staff cannot access management functions
- Monitor and log all cross-portal data access attempts

## Implementation Status

✅ **Completed**:
- Extended CloudFormation template with new infrastructure
- Staff portal API with restricted agent access
- New database tables with proper GSI design
- Knowledge Base integration via Strands SDK
- Data filtering and access control mechanisms

🔄 **In Progress**:
- Sample data generation for new tables
- Documentation updates
- UI components for staff portal

⏳ **Pending**:
- CloudFormation deployment testing
- End-to-end integration testing
- Material UI frontend implementation

The expanded architecture maintains the original design principles while adding robust multi-portal capabilities and comprehensive staff data management.