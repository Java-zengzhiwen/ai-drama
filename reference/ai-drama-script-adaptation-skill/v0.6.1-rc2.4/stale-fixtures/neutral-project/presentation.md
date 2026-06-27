# Creator Presentation

current_gate=SCRIPT_APPROVAL
approved_for_downstream=false
status=USER_ACCEPTANCE_REQUIRED

## 完整剧本

# Fixture Script

## Scene NA Alert Desk

Location: operations lab.
Time: morning.
Interior/Exterior: interior.
Characters: Engineer A, Team Lead B.
Atmosphere: tense.
Scene Goal: surface the alert.
Emotion Start: focused.
Emotion Progression: concern to action.
Emotion End: decisive.
Environment: workstations and status displays.

### Actions
Engineer A receives a safety alert before launch. Team Lead B refuses to ignore the alert.

### Dialogue
Engineer A: The safety alert is real.
Team Lead B: Ground the test drone until we know why.

### Performance Details
measured urgency

### Sound or Effective Silence
alert tone

### End State
drone grounding ordered

### End Hook
diagnostics begin
### RC2.2 Body Evidence Fixture Lines
### 动作
Engineer A receives a safety alert before launch
Team Lead B refuses to ignore the alert

## Scene NB Test Bay

Location: test bay.
Time: same day.
Interior/Exterior: interior.
Characters: Engineer A.
Atmosphere: clinical.
Scene Goal: confirm fault.
Emotion Start: worried.
Emotion Progression: testing to proof.
Emotion End: certain.
Environment: test drone and diagnostic bench.

### Actions
The test drone is grounded. A hidden sensor fault is confirmed by repeated diagnostics.

### Dialogue
Engineer A: The sensor fault repeats on every run.

### Performance Details
quiet concentration

### Sound or Effective Silence
machine hum

### End State
fault confirmed

### End Hook
review required
### RC2.2 Body Evidence Fixture Lines
### 动作
The test drone is grounded
A hidden sensor fault is confirmed

## Scene NC Review Room

Location: review room.
Time: afternoon.
Interior/Exterior: interior.
Characters: Team Lead B.
Atmosphere: formal.
Scene Goal: delay launch.
Emotion Start: grave.
Emotion Progression: risk to responsibility.
Emotion End: resolved.
Environment: conference table.

### Actions
Launch is delayed for a public safety review. The team documents the evidence.

### Dialogue
Team Lead B: Delay the launch and publish the safety review.

### Performance Details
steady tone

### Sound or Effective Silence
quiet room

### End State
review scheduled

### End Hook
public statement next
### RC2.2 Body Evidence Fixture Lines
### 动作
Launch is delayed for a public safety review

## 当前 Revision

n-v1

## 场次概览

See script JSON scenes.

## Strict Critical Beat Coverage

All critical fixture beats are covered by script-body evidence.

## Partial Beats

None.

## Production Assumptions

See production-assumption-log.json.

## Adaptation Extensions

See adaptation-extension-registry.json.

## Source Conflicts

See source-conflict-registry.json and source-claim-audit.json.

## Current Issues

None recorded for fixture validation.

## Recommended Decision

Human review required; no downstream approval is granted.

## Next After Approval

Only after explicit user acceptance may downstream planning begin.

## Revision Impact Scope

Script, JSON, coverage, hashes, and handoff must be regenerated after any revision.

Approval instruction: accept

Revision instruction: request_revision

Rejection instruction: reject
