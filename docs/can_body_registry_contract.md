# CAN Body Registry Contract

This repo provides vehicle CAN observation, interpretation, learning support, and vehicle-facing signal handling.

The canonical doctrine lives in:

- `velvet-ai-core/docs/retrofit_body_registry.md`
- `velvet-ai-core/docs/boot_identity_sequence.md`
- `velvet-ai-core/docs/naming_and_binding.md`

This document defines the vehicle CAN repo's local contract.

Velvet Vehicle CAN may help identify, classify, and validate vehicle body signals, but it must not treat detected CAN activity as trusted authority by itself.

Discovery does not equal trust.

Detection does not equal permission.

Reachability does not equal authorization.

## CAN Responsibilities

The CAN layer may:

- observe CAN traffic
- classify known and unknown frames
- propose signal meanings
- support vehicle fingerprinting
- report degraded or missing signals
- provide read-only telemetry events
- assist body registry validation
- help distinguish one vehicle body from another
- emit confidence-scored observations
- create or support discovery records

The CAN layer may not:

- directly authorize actions
- directly execute actuator commands without the gate
- treat learned signals as trusted without registration
- silently promote discovered signals to write-capable organs
- assume the current vehicle is the previous vehicle
- bypass capability token checks
- bypass safety gates
- bypass receipt logging
- treat CAN reachability as ownership or authority

## Body Registry Relationship

A vehicle body registry entry defines which CAN interfaces, signals, modules, and organs are known for a specific vehicle body.

Examples:

    body_id: tiburon_v0
    body_type: vehicle
    surface: drive
    can_profile: tiburon_v0_can_profile
    status: active

CAN-discovered signals should begin as candidates.

Candidate signals should not become trusted organs until reviewed, validated, registered, and receipt-backed.

## Candidate Signal Flow

Recommended flow:

    CAN signal detected
      -> candidate signal record created
      -> read-only observation
      -> confidence score assigned
      -> possible organ mapping proposed
      -> safety class proposed
      -> human or policy review
      -> body registry update
      -> receipt recorded
      -> capability policy assigned if needed

Candidate signals default to read-only.

Write-capable behavior requires explicit authorization.

## Vehicle Fingerprint Support

The CAN layer may assist boot identity by helping verify the expected vehicle body.

A vehicle fingerprint may include:

- known CAN identifiers
- expected module responses
- signal timing patterns
- configured bus interface
- registered hardware profile
- known degraded or missing modules
- previous validated body profile

A fingerprint mismatch must not result in blind execution.

Mismatch should trigger degraded mode, observe-only behavior, or review.

## Read vs Write Boundary

Read behavior and write behavior must remain separate.

Read examples:

- vehicle speed observation
- RPM observation
- coolant temperature observation
- door state observation
- light state observation
- steering angle observation

Write examples:

- lock command
- window command
- light command
- HVAC command
- throttle-related command
- brake-related command
- steering-related command

Write-capable CAN actions require the full authorization path.

## Required Flow for Write-Capable CAN Actions

Correct flow:

    requested CAN action
      -> intent event
      -> identity / context check
      -> policy authorization
      -> capability token check
      -> safety gate
      -> CAN executor
      -> receipt

Forbidden flow:

    learned CAN signal
      -> direct actuator command

## Runtime Startup Rule

At startup, CAN modules should begin observe-only until boot identity confirms:

- active body identity
- expected CAN profile
- receipt ledger availability
- capability policy availability
- safety profile availability
- executor authorization

If any of these are missing or mismatched, CAN behavior should degrade safely.

## Public Rule

CAN observes.

Registry records.

Policy authorizes.

Gates enforce.

Executors act.

Receipts remember.