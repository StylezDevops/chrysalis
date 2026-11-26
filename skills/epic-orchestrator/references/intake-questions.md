# Intake questions

Ask these together, in one message, after reading the description and CLAUDE.md. Skip any the description already answers, and say which ones you're skipping and why. The user's answers go into `intake.md`; anything that constrains builders goes into `rules.md`.

## Always ask

1. **Concurrency**: "How many subagents may run at once?" (Don't default. This is theirs to set; it drives cost and how much they'll be asked to review at each wave.)
2. **Extra rules**: "Beyond CLAUDE.md, any constraints every builder must follow?" Give prompts: language/framework version, forbidden dependencies, coding style not already captured, commit message format, test framework, no-network, anything they've been burned by before.

## Ask when not clear from the description

3. **Definition of done**: What must be true for the epic to be complete? Tests passing? Lint clean? Docs? A demo path?
4. **Out of scope**: Anything a builder might reasonably add that they don't want (auth, migrations, UI polish, telemetry...).
5. **Base branch**: Where does the integration branch start from, and what should it be called? Default: current branch, `epic/<slug>`.
6. **Existing decisions**: Anything already decided that a builder might re-decide (DB choice, API style, folder layout).
7. **Test expectations**: If the repo has no test suite: should builders write tests? Which framework?
8. **Review appetite**: Do they want a chat update after every wave, or only when a decision is needed?

## Do not ask

- Anything you can read from the repo (language, framework, layout, existing tests, CI config).
- Anything CLAUDE.md already states.
- Design questions that belong in the plan, those get answered at the gate, with the plan in front of them.
