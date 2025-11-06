# -*- coding: utf-8 -*-
"""
.. workflow-agent-selection:

AA Selection & Scoring
=============================

AgentScope now integrates an **AssistantAgent (AA)** module dedicated to
ranking and selecting downstream agents whenever the business requirement
is fully defined. The module translates the policy described in the
"Agent 选择与评分说明" into code, so the selection criteria remain visible
and auditable inside the project.

Roles & Boundaries
----------------------

AA is a **single, system-level agent** that becomes active only after a new
project has collected a stable set of requirements. It operates on a
per-role basis and is responsible for:

* keeping the static scores (``S_base``) up to date for every registered agent,
* evaluating the *dynamic* requirement fit for the current project,
* producing a ranked shortlist (default Top-5) and logging the decision path.

Static Score (``S_base``)
----------------------------

``S_base`` is calculated only when agents are created or when the platform
refreshes the profile. The score is a weighted sum of four components:

* **Performance** – Offline / online benchmark quality.
* **Brand recognition** – Official certifications or tiered partnerships.
* **User recognition** – Historical satisfaction, repeat users, renewal rate.
* **Fault ledger** – Active violations, cancellations, or policy breaches
  (automatically cooled down and deducted as penalties).

The default weights are configurable via ``StaticScoreWeights`` and are
normalized before use. A convenience API on ``AgentProfile`` recomputes
``S_base`` when severity weights or cooling rules change. Because these
values are cached, normal project execution does not recalculate them.

Dynamic Requirement Fit
--------------------------

Demand-specific attributes are captured in ``RoleRequirement``. The AA
module checks for hard constraints first (e.g., mandatory tools or
certifications) and drops candidates that do not qualify. For the remaining
agents, the ``RequirementFitScorer`` scores the overlap on skills, tools,
domains, languages, regions, and compliance tags. Each dimension provides a
coverage ratio, producing a fit score in ``[0, 1]`` together with detailed
matched / missing sets and rationales ready for UI display.

Selection Flow
-----------------

1. **Initial ranking** – All candidates that satisfy the hard constraints are
   sorted purely by ``S_base``. Only the next ``top_n`` (default 5) enter the
   shortlist for this round. If the user rejects the entire batch, AA can
   advance ``batch_index`` to fetch the next five.
2. **Demand-aware ranking** – For those ``top_n`` agents the selector computes
   the requirement fit and combines it with ``S_base``. Optional cold-start
   quotas add a capped bonus to new agents while guarding service quality.
3. **System default selection** – The highest combined score becomes the
   default recommendation. If the UI collects a user override, AA verifies
   that the choice is within the visible batch and records the decision as a
   "user" action.
4. **Audit logging** – Every round (including empty batches) is stored inside
   ``SelectionAuditLog`` together with ranking evidence, risk notes, and the
   final decision. This satisfies the policy's traceability requirement.

Tie-breaking strictly follows the specification: requirement fit, fault
count, performance, brand, recognition, and finally the most recent success.

Example
---------

.. code-block:: python

   from datetime import datetime, timedelta, timezone
   from agentscope.aa import (
       AssistantAgentSelector,
       AgentCapabilities,
       AgentProfile,
       RoleRequirement,
       RequirementHardConstraints,
       AAScoringConfig,
       StaticScore,
   )

   selector = AssistantAgentSelector(
       config=AAScoringConfig(top_n=5, requirement_weight=0.4),
   )

   dev_requirement = RoleRequirement(
       role="Backend",
       skills={"python", "asyncio", "fastapi"},
       tools={"docker", "k8s"},
       regions={"cn"},
       hard_constraints=RequirementHardConstraints(
           required_tools={"docker"},
           required_certifications={"iso27001"},
       ),
       notes="LLM infra integration",
   )

   agents = [
       AgentProfile(
           agent_id="a-001",
           name="EdgeOps",
           role="Backend",
           static_score=StaticScore(
               performance=0.92,
               brand=0.8,
               recognition=0.85,
           ),
           capabilities=AgentCapabilities(
               skills={"python", "fastapi", "redis"},
               tools={"docker", "k8s"},
               regions={"cn"},
               compliance_tags={"mlops"},
               certifications={"iso27001"},
           ),
           recent_success_at=datetime.now(timezone.utc) - timedelta(days=2),
       ),
       # ... additional profiles ...
   ]

   decision = selector.select(
       role="Backend",
       requirement=dev_requirement,
       candidates=agents,
   )

   print(decision.selected.profile.name)
   # Access recent audit trails for display
   timeline = selector.last_rounds()

The same API forms the basis for UI rendering: each ``CandidateRanking``
contains the combined score, ``S_base``, requirement-fit rationale, missing
items, and risk notes. Developers can feed this struct directly into console
logs, web dashboards, or AgentScope Studio plugins.

Cold Start & Fault Handling
-----------------------------

*Cold start* indicators per profile enable controlled exposure. The selector
allows a limited number of cold-start agents (quota configurable) to receive
an explicit bonus; extra cold-start entries are penalized so the shortlist
never becomes saturated with unproven agents.

The ``FaultLedger`` takes care of applying cooling windows automatically.
Critical incidents deduct a larger share of the ``fault`` component until the
cooling deadline passes. Because the ledger is injected into the profile,
platform operators can plug in their existing compliance feeds without
modifying the selection logic.

Key Guarantees
-----------------

* Only **requirement fit** is recomputed per project selection.
* ``S_base`` stays stable between selections unless the platform refreshes the
  agent profile.
* The selector enforces the policy sequence **S_base Top-5 → Demand-aware
  re-ranking → Default pick / user override → Optional batch rollover** and
  logs every decision for audit.
"""
