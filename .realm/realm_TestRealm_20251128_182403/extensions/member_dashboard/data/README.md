# Member Dashboard Extension Data

This directory contains initial data for the member dashboard extension.

## Data Files

### services_data.json

Contains public services available to members.

**Entity**: Service

**Fields**:
- service_id: Unique service identifier (e.g., "srv-001")
- name: Service name
- description: Service description
- provider: Service provider organization
- status: Service status (Active, Pending, Expired)
- due_date: ISO format timestamp for service deadline
- link: URL link to the service
- user: Reference to User entity ID
- metadata: Additional metadata as JSON string

### tax_records_data.json

Contains invoices (tax and billing records) for members.

**Entity**: Invoice

**Fields**:
- id: Unique invoice identifier (e.g., "invoice-001")
- amount: Invoice amount (float)
- due_date: ISO format timestamp for payment deadline
- status: Payment status (Pending, Paid, Overdue)
- user: Reference to User entity ID
- metadata: Additional information (e.g., "Income Tax - Annual personal income tax (2024)")

## Loading Data

These data files are automatically loaded during realm deployment via the automatic extension data loading feature.

When you run `realms realm create --deploy`, the system will:
1. Discover all `extensions/*/data/*.json` files
2. Import them automatically into the database

## Notes

- The `user` field references existing User entity IDs in your realm
- Default sample data uses user IDs "3" and "4" (user_001 and user_002)
- Services and tax records are filtered by user_id when queried
- Adjust user references and data based on your specific realm requirements
