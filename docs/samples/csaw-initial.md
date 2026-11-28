# CSAW: project definition

Generated 2026-11-28 from `config_project.json`. Sections marked TO DO need the project owner or a session of
interrogation (see the `chrysalis-init` skill). Everything else came from the config.

## Purpose

An audio effect plugin ported from a Python reference.

## Problem

The plugin must match the Python reference output.

## Users

- music producers

## Objectives

- (none given)

## Stage and stack

- Stage: new
- Languages: c++, python
- Frameworks: none named
- Platforms: desktop, plugin

## Risks flagged in the config

- realtime

## Rules in force

Universal:

- U1: Measure first
- U2: A check must be able to fail
- U3: A defect becomes structure
- U4: Tests argue, they do not record
- U5: Adversarial audit until a round is clean
- U6: Every fault is owned and on the record
- U7: A repeatable mistake gets a hook
- U8: One source of truth
- U9: Docs move with code
- U10: lusser, scaled to the change
- U11: Decisions carry their reasons
- U12: Sessions hand over
- U13: A report is a claim
- U14: Ask or decide
- U15: Test what changed
- U16: Parallel work is earned
- U17: Fail closed
- U18: Every unit has one outcome
- U19: Config is checked when it loads
- U20: A mechanism counts once it is shown to run
- U21: One promise, every member

Conditional:

- K5 (because `risk.realtime`)
- K7 (because `ci.remote == "on-request"`)

## Architecture

TO DO: components, the boundaries between them, data that persists, and what talks to the outside
world. Record each lasting choice as an ADR in `docs/adr/`.

## Constraints

TO DO: platform, licence, budget, performance and compliance limits, each with its source.

## Risks and how they are checked

TO DO: for each risk, the gate in `gates.toml` or the human check that would catch it.

## Approach

TO DO: first milestone, what "working" means for it, and the first 3 to 5 backlog items.

## Open questions

TO DO: anything the config could not answer. Each one goes to them before work that depends on it.
