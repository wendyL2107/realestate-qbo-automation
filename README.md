# Real Estate Deal Automation & QuickBooks Online (QBO) Pipeline

An automated backend workflow pipeline built in Python to orchestrate real estate transaction ingestion and synchronize financial operations with the QuickBooks Online (QBO) Accounting API.

## System Architecture

```text
[Incoming Deal Event (JSON)]
            │
            ▼
[Python Business Logic Engine] ──► (Dynamic Tier & Commission Computation)
            │
            ├─► POST /v3/company/{realmId}/customer  (QBO Customer Ingestion)
            └─► POST /v3/company/{realmId}/invoice   (QBO Invoice Generation)
