# {{title}}: Definition of Ready and Done

## Ready

A story or register row can start when:

- [ ] its acceptance criteria are observable results, not activities;
- [ ] its lusser spec exists and every ambiguity in it has a human's answer (U10);
- [ ] the gates it touches are named;
- [ ] for a live system, its blast-radius class and rollback are written down (K1, when in force);
- [ ] it fits in 1 session, or it has been split.

## Done

A story or register row is done when:

- [ ] each acceptance criterion has been shown, with a pointer to the evidence;
- [ ] every new or changed check has been seen to fail on the defect it targets (U2);
- [ ] the build, the unit tests and the touched gates pass, read by exit code (U13, U15);
- [ ] `lusser.py check` passes;
- [ ] docs changed with the code (U9);
- [ ] for a defect: the register row is CLOSED with its numbers, test and follow-up (U3);
- [ ] the handover is rewritten (U12).
