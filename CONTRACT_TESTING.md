# Git Contract Testing with DynamoDB

## Problem Statement

Teams share code scripts (e.g. data pipelines) across multiple users and consumers.
When a developer changes a script, there is no automated way to know if the change
breaks what consumers depend on — wrong columns, wrong data types, missing fields.
Bugs only surface in production, causing downstream failures and lost trust.

---

## Solution Overview

A contract testing system where:
- **Consumers** define what they expect from a script (columns, data types)
- **Contracts are stored in DynamoDB** — centralised, visible, and updatable by anyone
- **A git pre-push hook** fetches and runs all contracts before any push is allowed
- **Pushes are blocked** if any contract is violated

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONSUMERS / USERS                        │
│                                                                 │
│   User A defines:              User B defines:                  │
│   ┌─────────────────┐          ┌─────────────────┐             │
│   │ Contract        │          │ Contract        │             │
│   │ - user_id: int  │          │ - amount: float │             │
│   │ - email: str    │          │ - created_at:   │             │
│   │                 │          │   datetime      │             │
│   └────────┬────────┘          └────────┬────────┘             │
└────────────┼────────────────────────────┼─────────────────────-─┘
             │   write contracts          │
             ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AWS DynamoDB                            │
│                                                                 │
│   Table: pipeline_contracts                                     │
│   ┌──────────────┬──────────┬───────────────────────────┐      │
│   │ contract_id  │  owner   │       columns             │      │
│   ├──────────────┼──────────┼───────────────────────────┤      │
│   │ pipeline_A   │  User A  │ [{user_id, int64}, ...]   │      │
│   │ pipeline_B   │  User B  │ [{amount, float64}, ...]  │      │
│   └──────────────┴──────────┴───────────────────────────┘      │
└─────────────────────────────┬───────────────────────────────────┘
                              │  fetch all contracts
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DEVELOPER MACHINE                          │
│                                                                 │
│   $ git push                                                    │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────┐    fetch     ┌──────────────┐                │
│   │  pre-push   │ ──────────── │   DynamoDB   │                │
│   │    hook     │              └──────────────┘                │
│   └──────┬──────┘                                              │
│          │  run                                                 │
│          ▼                                                      │
│   ┌─────────────────┐                                          │
│   │ run_contracts.py│                                          │
│   │                 │                                          │
│   │ ✅ contract A   │                                          │
│   │ ❌ contract B   │──── PUSH BLOCKED                        │
│   └─────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Use Case Flow

```
1. Consumer defines contract   →   stored in DynamoDB
2. Developer changes pipeline  →   git push triggered
3. pre-push hook fires         →   fetches all contracts from DynamoDB
4. run_contracts.py runs       →   executes pipeline, checks output
5a. All pass                   →   push allowed ✅
5b. Any fail                   →   push blocked ❌ with clear error
```

---

## Key Benefits

⭐ **No broken pipelines in production**
   Issues are caught before code leaves the developer's machine.

⭐ **Consumer-owned contracts**
   Users define what they need. Developers don't have to guess downstream requirements.

⭐ **Centralised in DynamoDB**
   One source of truth. No scattered config files. Visible and updatable by all stakeholders.

⭐ **Zero friction for consumers**
   No code required. Users simply define expected columns and data types in a DynamoDB record.

⭐ **Automatic enforcement**
   No manual review step. Git itself is the gatekeeper — enforcement is built into the workflow.

⭐ **Scales across teams**
   Any number of users can register contracts against any script independently.

---

## Example: Developer Experience

When a push violates a contract, the developer sees:

```
$ git push origin main

Running contract tests...
❌ pipeline_B (owner: User B):
   'amount': expected float64, got int64
   'created_at': missing column

❌ Push blocked: contract tests failed
```

The developer knows exactly what broke and whose contract was violated — before anyone is impacted.

---

## Repository Structure

```
repo/
├── pipeline.py                    ← pipeline script (must expose run() → DataFrame)
├── tests/
│   ├── contracts/                 ← local fallback contracts (yaml)
│   │   └── pipeline.yaml
│   └── run_contracts.py           ← fetches from DynamoDB, validates pipeline output
└── .git/hooks/pre-push            ← triggers contract tests on every push
```

---

## DynamoDB Contract Record Format

```json
{
  "contract_id": "pipeline_A",
  "owner": "User A",
  "script": "pipeline.py",
  "output_columns": [
    { "name": "user_id",    "dtype": "int64"         },
    { "name": "email",      "dtype": "str"           },
    { "name": "created_at", "dtype": "datetime64[us]"},
    { "name": "amount",     "dtype": "float64"       }
  ]
}
```

---

## How to Add a Contract (Consumer Steps)

1. Log into AWS Console → DynamoDB → `pipeline_contracts` table
2. Create a new item with your expected columns and data types
3. From that point on, any push that breaks your contract will be automatically blocked

No code. No pull requests. No waiting.
