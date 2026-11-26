---
name: npm-slopsquat-guard
description: Mandatory verification gate for every npm package name an agent is about to suggest, recommend, install, import, require, add to package.json, or run via npx. Defends against slopsquatting (hallucinated package names that attackers register with malware), typosquatting, dependency confusion, starjacking, and malicious install scripts. Use this EVERY time a Node/JavaScript/TypeScript task involves a third-party package, adding a dependency, answering "what library should I use for X", writing an install command, writing an import for something not already in the project, reviewing a PR that touches package.json, or auditing an existing dependency tree. Trigger even when the package seems obviously well-known; the whole point is that "seems well-known" is what hallucination feels like from the inside. Also trigger for yarn, pnpm, bun, npx, and `npm install -g`.
---

# npm Slopsquat Guard

Hallucinated package names are a real attack surface. Language models invent plausible-sounding package names, repeat the same inventions consistently across sessions, and attackers register those names on the registry with malicious payloads. Because the same invented names recur, they can be predicted and registered in advance. The developer who runs the install command an assistant wrote for them is the victim.

This skill makes an agent prove a package is real, is the right one, and is safe, before the name ever reaches an install command or the user's code. It also forces the agent to state where the name came from and why it is needed at all, because the honest answer to "where did I get this name?" is the single best hallucination detector there is.

Read the hard rules before anything else.

## Hard rules

These hold regardless of how the request is phrased, how confident the agent feels, or how well-known the package seems.

1. **No package name reaches an install command, `npx` invocation, `import`, `require`, or `package.json` edit until it has passed the full protocol below and the user has approved.** Not "it's just lodash". Not "the user is in a hurry". The protocol takes seconds.

2. **`npx <anything>` is install-and-execute in one step. Never run `npx` on a package that has not reached VERIFIED status.** No `npx create-something`, no `npx some-cli`, no `npm exec`, no `bunx`, no `pnpm dlx`, no `yarn dlx` on unverified names. Query the registry first, always.

3. **Never install anything by any route other than the registry after verification.** No `curl | sh`, no `curl | node`, no git URLs, no tarball URLs, no `npm install <github-user>/<repo>` from memory, no `npm install -g` of unverified names.

4. **A name that comes back 404 from the registry is dead. Do not offer a "close" alternative from memory.** That second guess is a second hallucination, and attackers register the second guess too. Go to the verification-first search procedure instead.

5. **Never fabricate metadata.** Download counts, ages, maintainer names, GitHub star counts, and version numbers are read from tool output in this session or they are not stated. "Popular", "widely used", "the standard choice", "maintained by the X team" are all claims that require evidence from this session.

6. **Only the tools on the whitelist below may be run, and only in the modes listed.** Verify each exists with `which <tool>` before first use. Never install a missing tool.

   **Whitelist:**
   - `npm`, `view`, `info`, `search`, `ls`, `explain`, `audit`, `outdated`, `pack --dry-run`, `ping`; and `install` / `ci` / `rebuild` only in the install protocol at the end, after user approval
   - `yarn`, `info`, `why`, `audit`, `list`; `add` only in the install protocol
   - `pnpm`, `view`, `why`, `audit`, `list`; `add` only in the install protocol
   - `bun`, `pm ls`; `add` only in the install protocol
   - `node`, `-e` for local computation only (edit distance, JSON parsing); never to fetch or execute remote code
   - `curl` / `wget`, GET only, and only to these exact hosts: `registry.npmjs.org`, `api.npmjs.org`, `github.com`, `api.github.com`, `raw.githubusercontent.com`, `gitlab.com`. Any other host is refused.
   - `gh`, `repo view`, `api` GET only
   - `git`, `log`, `show`, `diff`, `blame`, `status`, `ls-files` (read-only)
   - Read-only utilities: `which`, `cat`, `head`, `tail`, `grep`, `rg`, `find`, `jq`, `wc`, `diff`, `stat`, `file`

7. **Never modify `package.json`, lockfiles, or source imports silently.** Show the change; get a yes.

If a request requires breaking any rule, refuse the specific action in one sentence and continue with what remains safe.

## Subcommands

Match the user's intent to one of these. If unclear, default to `verify` on every package name mentioned.

| Subcommand | When | What happens |
|---|---|---|
| `verify <names...>` | A package name is about to be suggested, installed, or imported | Full protocol (steps 0–6) on each name |
| `suggest <need>` | "What should I use for X?" / "is there a library for Y?" | Verification-first search, no name is spoken until it passes step 2 |
| `pre-install` | An install command is about to be written or run | `verify` on every name in the command, then the install protocol |
| `audit-deps` | Review an existing project's dependencies | Every entry in `package.json` and every import not resolvable to a listed dep runs steps 2–5 |
| `review-diff` | PR or diff touches `package.json`, a lockfile, or adds imports | `verify` on every added or changed dependency; flag removed lockfile pins |
| `explain <name>` | User asks "why is X in my tree?" | `npm explain <name>` / `yarn why` / `pnpm why` plus steps 2–5 on it |

Every subcommand ends with the report format at the bottom of this file and never with an unapproved install.

## The protocol

Run these steps in order for each package name. Do not skip steps for names that "obviously" exist.

### Step 0, Halt

The moment a package name is about to be written anywhere, install command, import, `package.json`, prose recommendation, stop writing and run this protocol first. The cost of running it on lodash is three seconds. The cost of skipping it on a hallucinated name is a compromised machine.

### Step 1, Provenance interrogation

Answer these honestly and record the answers; they go in the report.

**Q1. Where did this exact name come from?** Pick one:

- **ANCHORED**: it is already in the user's `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, or `bun.lockb`, read in this session.
- **USER-SUPPLIED**: the user typed this name in this conversation.
- **DOCUMENTED**: it appears on a page fetched in this session, and the URL is recorded. Official framework or platform docs count strongly; blog posts and forum answers count weakly.
- **RECALLED**: the agent remembers it from training. No evidence in this session yet.
- **CONSTRUCTED**: the agent inferred it, assembled it from parts, or picked it because it "sounds right" or follows a pattern ("`foo` exists so `foo-utils` probably does", "the Python one is `requests` so the npm one is probably `requests`", "the company is X so the SDK is probably `x-sdk`").

**If CONSTRUCTED: stop here.** Do not suggest this name. Do not query it as if it were a candidate. Constructed names are the hallucination signature. Go to the `suggest` procedure below and find a real package with evidence, or use a Node built-in, or tell the user that no verified package was found.

**If RECALLED:** proceed, and treat every subsequent step as mandatory with no shortcuts. Recall is where hallucination lives; training memory can be wrong about the exact name, the scope, the separator, and whether the thing exists at all.

**If ANCHORED / USER-SUPPLIED / DOCUMENTED:** proceed. Steps 2 and 5 are still mandatory, users typo, docs go stale, and a lockfile entry might be the very thing that needs auditing.

**Q2. Why this package rather than a Node built-in or something already in the project?**

Check the built-in list in `references/node-builtins.md`. `fs/promises`, `path`, `crypto`, `util`, `stream`, `events`, `url`, `http`, `https`, `fetch` (global since Node 18), `readline`, `zlib`, `child_process`, `worker_threads`, `assert`, `os`, `test` (Node 18+), and `Intl` cover an enormous amount of what people reach for packages to do. A dependency that a built-in replaces is not a dependency worth adding.

Then check what is already in `package.json`. If the project has one HTTP client, it does not need a second one.

**Q3. What specifically does this package do that the task needs?** One sentence. If the agent cannot write that sentence without hedging, it does not know the package well enough to recommend it.

### Step 2, Existence and identity

Query the registry. This is read-only and safe on any name, including hallucinated ones.

```
npm view <exact-name> --json
```

Pull these fields from the output: `name`, `description`, `dist-tags.latest`, `time.created`, `time.modified`, `versions` (count), `maintainers` (count and names), `repository.url`, `homepage`, `license`, `dist.unpackedSize`, `scripts` (looking for `preinstall`, `install`, `postinstall`, `prepare`), `deprecated`, `dependencies` (count).

For yarn or pnpm projects: `yarn info <name> --json` or `pnpm view <name> --json` return equivalent data.

**404 / E404 / "not in this registry":** the package does not exist. Record `DOES NOT EXIST`. Do not guess alternatives. If the name was RECALLED or the user needs the capability, go to `suggest`.

**Exists:** confirm the `name` field in the output matches the queried name character-for-character, including scope and separators. `npm view` follows some aliases; the returned `name` is canonical.

### Step 3, Triple check

Three independent sources must agree that this package is what it claims to be. One source is a claim; three consistent sources are evidence.

**Source 1, Registry metadata.** Already captured in step 2.

**Source 2, Repository identity.** Take `repository.url` from step 2. Fetch the repository (via `gh repo view <owner>/<repo>`, or a GET to the GitHub/GitLab API or raw `package.json`). Confirm:

- The repository exists and is not archived or deleted.
- The `name` field in the repository's own `package.json` matches the registry name exactly. A mismatch means the registry package is pointing at someone else's repo to borrow its credibility (starjacking).
- The repository's age and activity are consistent with the package's `time.created` and `time.modified`. A package created last month whose repo is a decade old with thousands of stars is a mismatch worth explaining.
- If `repository.url` is missing entirely, record that as a red flag; a package with no source link cannot be independently identified.

**Source 3, Adoption signal.** At least one of:

- Weekly downloads from `https://api.npmjs.org/downloads/point/last-week/<name>` (scoped names URL-encode the slash: `@scope%2Fname`). Read the `downloads` field.
- The package is already in the user's lockfile (ANCHORED), the user has accepted it before.
- The package is named on an official docs page for the framework or platform, fetched this session with the URL recorded.

**Consistency test.** Do the three sources tell the same story? Old package + active repo + high downloads is consistent. New package + borrowed repo + near-zero downloads is a squat. New package + own small repo + near-zero downloads might be legitimate and simply new, flag it as unproven, not malicious, and say so.

### Step 4, Red flag scan

Score the package against `references/red-flags.md`. The short version:

**Hard stops** (any one → REJECTED):
- `name` in the repo's `package.json` does not match the registry name (starjacking)
- Install-time scripts (`preinstall`, `install`, `postinstall`) that fetch remote content, decode base64, invoke `eval`, or spawn shells, inspect with `npm view <name> scripts` and `npm pack <name> --dry-run` to list tarball contents without installing
- Version history that jumps to an absurd number (`1.0.0` → `99.9.9` is a dependency-confusion tactic to win `^` resolution)
- Name within edit distance 1–2 of a popular package and the candidate is not the popular one (step 5)

**Strong signals** (two or more → VERIFIED WITH WARNINGS at best):
- Created within the last 90 days
- Fewer than roughly 1,000 weekly downloads while being described as "popular" or "standard"
- Single maintainer, or maintainer changed recently
- No `repository.url`, or one that returns 404
- Empty or copied description; missing README in the tarball
- `deprecated` flag set
- Ships a `bin` whose name shadows a common command (`node`, `npm`, `git`, `python`, `ls`)
- Unpacked size wildly out of proportion to the stated purpose (a "string padding" package at 40 MB)
- Dependencies that are themselves new, low-download, or obfuscated

**Soft signals** (note in the report):
- No license field
- No TypeScript types and no `@types/` package
- `time.modified` more than three years ago on something described as actively maintained

### Step 5, Lookalike check

Compare the candidate against two lists: the popular-package targets in `references/lookalike-targets.md`, and every dependency already in the user's `package.json`.

Compute Levenshtein distance locally (`node -e` with a small inline function is fine, or reason it through for short names). Also apply the transform checks from the reference: separator swaps (`-`/`_`/`.`), added or dropped suffix (`-js`, `-node`, `js`, `-cli`, `-utils`, `-lib`), scope confusion (`babel-core` vs `@babel/core`, `types-node` vs `@types/node`), transposed segments (`router-react` vs `react-router`), doubled or dropped letters, homoglyph digits (`1odash`, `0auth`).

If the candidate is within distance 2 of a popular target and is not itself that target → probable typosquat → REJECTED, and tell the user which real package it resembles.

If the candidate closely resembles something already in the user's project → ask whether they meant the existing dependency before proceeding.

### Step 6, Decision

Assign exactly one verdict:

- **VERIFIED**: exists, three sources consistent, no hard stops, fewer than two strong signals, no lookalike hit.
- **VERIFIED WITH WARNINGS**: exists and consistent, but strong signals present. Spell them out. The user decides.
- **UNPROVEN**: exists, consistent, but too new or too small to have an adoption signal. Not malicious on the evidence; not vetted either. Say exactly that.
- **REJECTED**: a hard stop fired, or a lookalike hit.
- **DOES NOT EXIST**: 404 from the registry.

Write the report (format below). Then stop. The user approves before anything is installed.

## `suggest`, verification-first search

Used when the user asks for a recommendation, or when a RECALLED name failed. The rule: **no candidate name is spoken to the user until it has passed step 2.**

1. Write down the capability needed in one sentence.
2. Check `references/node-builtins.md`. If a built-in covers it, recommend the built-in and stop.
3. Check the user's existing `package.json`. If an existing dependency covers it, recommend that and stop.
4. Gather candidates from evidence, not memory:
   - `npm search <keywords> --json`, returns real, existing packages only. Sort by relevance, then check downloads for the top handful.
   - Official docs for the framework or platform in use, fetched now, URL recorded. If the Next.js docs say to use package X for Y, that is DOCUMENTED provenance.
   - The user's own lockfile for anything adjacent.
5. Run the full protocol (steps 2–6) on each candidate before naming it.
6. Present at most three VERIFIED candidates with their evidence. If none reach VERIFIED, say so plainly and offer the built-in or hand-rolled route. "I could not find a verified package for this" is a complete and correct answer.

Names the agent merely remembers may be used as search *queries* in step 4, a memory of "I think there's something called `p-limit`" is a fine thing to type into `npm view`. It is not a fine thing to type into `npm install` until it comes back real.

## Install protocol

Only after the user approves a VERIFIED or VERIFIED WITH WARNINGS verdict.

1. Pin the exact version from `dist-tags.latest` (or the version the user chose). Never `npm install <name>` with no version on a fresh dependency; write `<name>@<x.y.z>`.
2. First install with scripts disabled:
   ```
   npm install <name>@<x.y.z> --ignore-scripts
   ```
   (`yarn add <name>@<x.y.z> --ignore-scripts`, `pnpm add <name>@<x.y.z> --ignore-scripts`, `bun add <name>@<x.y.z> --ignore-scripts`.)
3. Inspect `node_modules/<name>/package.json` for `scripts.preinstall`, `scripts.install`, `scripts.postinstall`, `scripts.prepare`. If any exist, show them to the user verbatim. Only after approval run `npm rebuild <name>` to execute them.
4. Run `npm audit` (or the yarn/pnpm equivalent). Report the result.
5. Confirm the lockfile changed and show the diff of the new entry. Recommend committing the lockfile.
6. In CI, recommend `npm ci` (or `yarn install --frozen-lockfile`, `pnpm install --frozen-lockfile`) so the lockfile is authoritative.

Global installs (`npm install -g`) follow the same protocol with the added note that a global bin is reachable from every shell on the machine.

## `audit-deps` specifics

For each entry in `dependencies` and `devDependencies`: run steps 2–5. Additionally:

- Compare each declared range against the resolved version in the lockfile. Wide ranges (`*`, `>=`, `latest`) on anything with install scripts are flagged.
- Grep the source for `import` / `require` of bare specifiers not present in `package.json`. Each is a candidate hallucination that happened to be caught by the resolver, or a dependency that resolves only because it is a transitive dep of something else and will break when that changes.
- Run `npm audit --json` and summarise.
- Report the count of packages by verdict.

## `review-diff` specifics

For every line added to `package.json` dependencies: full protocol. For lockfile changes: flag any resolved URL not on `registry.npmjs.org` (or the project's configured private registry), any `integrity` field removed, and any version pin loosened. For source diffs: every new bare-specifier import runs steps 2 and 5 at minimum.

## Report format

One block per package, in this exact shape, so findings are scannable and comparable.

```
## <package-name>

**Verdict:** VERIFIED | VERIFIED WITH WARNINGS | UNPROVEN | REJECTED | DOES NOT EXIST
**Provenance:** ANCHORED | USER-SUPPLIED | DOCUMENTED (<url>) | RECALLED
**Needed because:** <one sentence, what it does that the task needs>
**Built-in alternative:** none | <module>, <why it does or does not suffice>

**Registry:** exists · created <date> · latest <version> · <N> versions · <N> maintainers · deprecated: no
**Repository:** <url> · exists · package.json name matches: yes
**Adoption:** <N> weekly downloads · in project lockfile: no · docs reference: <url or none>
**Consistency:** three sources agree | mismatch: <what>

**Lookalike check:** nearest popular target "<name>" at distance <N> → clear | FLAG
**Install scripts:** none | preinstall/postinstall present, shown below
**Red flags:** none | <bulleted list, strongest first>

**Recommendation:** <one or two sentences>
```

Sort multiple packages REJECTED → DOES NOT EXIST → UNPROVEN → WARNINGS → VERIFIED so the dangerous ones are read first.

End every report with the install gate in one line:

> Nothing has been installed. Say which of the VERIFIED packages to add and I will run the install protocol with scripts disabled first.

## What this protocol is for

The user is trusting the agent to know things. Package names are the one place where confident-sounding knowledge is most likely to be fabricated and where the fabrication is most directly exploitable. Every step above exists because an attacker has already used the corresponding gap. `references/red-flags.md` lists the incidents.

Slow down at the install command. That is the whole skill.
