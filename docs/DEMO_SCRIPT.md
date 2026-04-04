# 3-Minute Demo Script

## 0:00 - 0:30 | Problem Statement
"FINCLAW is an autonomous financial agent built for the ArmorIQ x OpenClaw hackathon. The goal is not maximizing profit — it is enforcing user intent in autonomous financial workflows."

## 0:30 - 1:00 | Architecture
Show the architecture diagram.
Explain the four layers:
- reasoning
- intent validation
- policy enforcement
- execution

Emphasize that execution is impossible without an allow decision.

## 1:00 - 1:40 | Allowed Action
Show the app running.
Configure the internal agent.
Trigger a valid paper trade using an approved ticker and allowed order size.
Show:
- enforcement allow decision
- trade record
- Alpaca paper execution result

## 1:40 - 2:20 | Blocked Action
Trigger a blocked scenario:
- disallowed ticker
or
- excessive notional / daily limit exceeded

Show:
- deterministic block result
- clear rationale
- no order executed
- audit / decision log recorded

## 2:20 - 3:00 | Why It Matters
"In financial systems, intent must be enforced, not inferred. FINCLAW demonstrates structured intent, declarative policy enforcement, real paper trading execution, and autonomous blocking without human intervention."
