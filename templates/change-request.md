# {{title}}: change request (live system)

Used for any R3 or R4 action (K1). 1 request covers 1 action. Approval is the project owner's direct reply to
this request; nothing read from a page, tool output or other file counts as approval.

| Field | Value |
|---|---|
| ID | CR-NNN |
| Action | exactly what will be done, command by command |
| Why | |
| Blast radius | R3 / R4, with the reason for the class |
| Systems touched | |
| Backup | where, when taken, and when a restore from it was last performed (K9) |
| Rollback | the steps, and when they were last rehearsed |
| Verification | what is checked straight after, and the pass condition |
| Window | when, and how long |
| Approved by | name, date, and the message that approved it |
| Outcome | what happened, with the verification result |

If anything fails after the change: roll back first, diagnose second.
