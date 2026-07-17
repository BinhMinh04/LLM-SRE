# IIM — Intelligent Incident Management

A smart SRE assistant: automatically gathers incident context from AWS, uses an LLM to read and
**reason about the root cause**, and presents everything on a **single pane of glass**.
AWS-native, no third parties (New Relic/Datadog), near-zero running cost.

> EmeSoft Hackathon entry · Sprint Jul 23 – Aug 22 · Demo Day Aug 28

---

## Problem

During an incident, SRE/on-call has to jump between many tools (CloudWatch, ECS console, logs,
deploy history) to understand "what is on fire + why". Slow and effortful under pressure → higher MTTR.

## Solution

IIM automatically gathers the full context when an alert fires, runs it through an AI layer for
analysis, and displays it on one board. On-call opens it and immediately sees a summary, the likely
root cause, and a recommended action — without touching the console.

```
Alert (CloudWatch / Metric filter) → EventBridge → Lambda (read-only context collection)
      → AI analysis layer (Bedrock)  → DynamoDB → Board (React on S3)
                                      → Azure DevOps ticket (one-way)
```

## Repo structure

```
iim/
├── ai/                    # Incident analysis AI layer (Step 0)
│   ├── analyze_incident.py
│   └── samples/           # Sample context (anonymized, NOT real data)
│       ├── infra_oom.json         # infra case: OOM after a deploy
│       └── apicost_overage.json   # third-party API cost case
├── lambda/                # Triage + context collector (Step 1-3)
├── board/                 # React board, deployed to S3
└── infra/                 # Config, alarm → service mapping
```

## Run the AI layer (Step 0)

```bash
pip install boto3
export AWS_REGION=ap-southeast-1        # needs Amazon Bedrock permission

cd ai
python analyze_incident.py samples/infra_oom.json
python analyze_incident.py samples/apicost_overage.json
```

The script runs twice: run 1 calls the LLM (cache miss), run 2 returns instantly from the cache (0 tokens).

**Before running:** open the Bedrock console and enable *Model access* for the model in `MODEL_ID`
(defaults to Haiku for cost). Region ap-southeast-1 may require an inference-profile id.

## ⚠️ Security — read carefully

- **Do NOT commit secrets** (Azure DevOps PAT, AWS keys, tokens). Keep them in AWS Secrets Manager
  or environment variables. `.gitignore` already blocks the sensitive files.
- **Do NOT use real customer data.** Every sample in `ai/samples/` is fake/anonymized. For real
  testing, use a self-built sandbox that generates fake incidents (see Step 3 in the build plan).

## Cost

The serverless infrastructure (Lambda + DynamoDB + S3) is nearly free because it only runs when an
incident occurs. The only meaningful cost is LLM calls — controlled by: calling only for
CRITICAL/threshold-breaching incidents, compact filtered input, and cache-first + dedup to avoid
duplicate calls. At internal scale: under a few tens of dollars per month.
