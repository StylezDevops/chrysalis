# Solidity, where to dig

Assume the caller is an adversary with unlimited capital, MEV access, and the ability to be first or last in a block. The question is never "would someone do this", it's "is it profitable".

**State transitions**: Enumerate contract states and the functions that move between them. Look for transitions callable in the wrong state, missing checks that a state was reached legitimately, and functions that update state after an external call (checks-effects-interactions violated).

**Economic incentives**: Who profits from each function being called at an unexpected time, with unexpected arguments, or in an unexpected order? Griefing (costless harm to others), sandwiching, front-running parameter changes, exploiting rounding direction, dust attacks on share-based accounting (first-depositor inflation).

**Access control**: `onlyOwner`/role modifiers on every privileged function? `initialize` callable more than once or by anyone? `tx.origin` used for auth? Role admin rights that let a lesser role escalate? Functions that should be `internal` but are `public`?

**Upgradeability**: Storage layout collisions between proxy and implementation; uninitialised implementation contracts (`_disableInitializers`); `selfdestruct` in an implementation; `delegatecall` to user-controlled addresses; upgrade authority and timelock.

**Oracle assumptions**: Spot price from a single DEX pool (flash-loan manipulable); stale prices (no heartbeat/timestamp check); decimals mismatches; Chainlink round completeness; TWAP window too short; hard-coded assumption that an asset is pegged.

**Reentrancy**: Not just ETH transfers: ERC-777 hooks, ERC-721/1155 `onReceived` callbacks, any external call to an address the user influences. Cross-function and cross-contract reentrancy where the guard is per-function. Read-only reentrancy affecting view functions other protocols consume.

**Governance abuse**: Flash-loan voting power, proposal execution without timelock, quorum manipulable, emergency powers with no expiry, admin keys that can drain.

**Value extraction opportunities**: Anywhere value moves: fees rounding to zero, fee-on-transfer and rebasing tokens breaking balance assumptions, `transfer` return values unchecked (use `SafeERC20`), `msg.value` in loops, self-transfer edge cases, `block.timestamp` as randomness.

**Tools E should reach for**: `slither`, `mythril`, `foundry` (`forge test` with fuzzing and invariant tests, `forge coverage`), `echidna`/`medusa` for property testing, `aderyn`. Fork tests against mainnet state where oracle or composability assumptions matter.
