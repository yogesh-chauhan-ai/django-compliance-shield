# Jurisdiction Coverage

django-compliance-shield covers the following jurisdictions out of the box.

## Supported jurisdictions

| Code  | Region          | Primary Law           | DSR Deadline | Breach Notification |
|-------|-----------------|-----------------------|-------------|---------------------|
| `IN`  | India           | DPDP Act 2025         | 30 days     | 72 hours to DPB     |
| `US`  | United States   | CCPA / FCRA           | 45 days     | 72 hours (Cal AG)   |
| `EU`  | European Union  | GDPR                  | 30 days     | 72 hours to SA      |
| `UK`  | United Kingdom  | UK GDPR               | 30 days     | 72 hours to ICO     |
| `CA`  | Canada          | PIPEDA / Bill C-27    | 30 days     | As soon as feasible |
| `AU`  | Australia       | Privacy Act 1988      | 30 days     | 30 days to OAIC     |
| `AE`  | UAE             | Federal DL No.45/2021 | 30 days     | 72 hours            |
| `SA`  | Saudi Arabia    | PDPL                  | 30 days     | 72 hours            |
| `OTHER`| All others     | Best-effort defaults  | 30 days     | 72 hours            |

## Country to jurisdiction mapping

The middleware automatically maps country names to jurisdiction codes:

```
India                 → IN
United States, USA    → US
Germany, France, Italy, Spain, Netherlands, Belgium,
Sweden, Poland, Denmark, Finland, Austria, Portugal,
Ireland, Greece, Czechia, Romania, Hungary            → EU
United Kingdom, UK    → UK
Canada                → CA
Australia             → AU
UAE, United Arab Emirates → AE
Saudi Arabia, KSA     → SA
Singapore, Japan, South Korea → OTHER
```

## FCRA specific note (US)

If your application performs employment background verification in the US,
you may qualify as a Consumer Reporting Agency (CRA) under FCRA.
This requires:

- Registering with the CFPB
- Providing FCRA Summary of Rights to consumers
- Following adverse action notice procedures (pre-adverse + 5 day wait + final)
- Allowing consumers to dispute inaccurate information within 30 days

The library provides the `fcra_dispute` and `fcra_adverse_action` DSR types
to support these workflows, but you must consult a US employment law attorney
before operating as a CRA.

## Retention policies seeded per jurisdiction

`python manage.py compliance_setup` seeds the following policies:

| Jurisdiction | Category            | Retention | Action    |
|-------------|---------------------|-----------|-----------|
| IN          | employment_records  | 3 years   | anonymise |
| IN          | pan_aadhaar         | 2 years   | anonymise |
| IN          | consent_records     | 7 years   | archive   |
| IN          | audit_logs          | 5 years   | archive   |
| IN          | session_data        | 30 days   | delete    |
| US          | employment_records  | 7 years   | anonymise |
| US          | ssn                 | 7 years   | anonymise |
| US          | consent_records     | 7 years   | archive   |
| US          | audit_logs          | 7 years   | archive   |
| EU          | employment_records  | 3 years   | anonymise |
| EU          | consent_records     | 5 years   | archive   |
| ...         | (29 total)          |           |           |
