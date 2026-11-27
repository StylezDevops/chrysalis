# {{title}}: Definition of Ready and Done

## Ready

A story or register row can start when:

- [ ] its acceptance criteria are observable results, not activities;
- [ ] its lusser spec exists and every ambiguity in it has a human's answer (U10);
- [ ] the gates it touches are named;
- [ ] any public surface it adds (route, endpoint, command, option) is named in the spec (U14);
- [ ] for code that moves data, its journey is written down (K10, when in force);
- [ ] for a live system, its blast-radius class and rollback are written down (K1, when in force);
- [ ] it fits in 1 session, or it has been split.

## Done

A story or register row is done when:

- [ ] each acceptance criterion has been shown, with a pointer to the evidence;
- [ ] each new mechanism (middleware, hook, service, option, alert) has been seen running on a real
      path, and `docs/verification.md` has a dated row for it (U20);
- [ ] new config is rejected at load when it is wrong, and each new option has a test of its
      effect (U19);
- [ ] no deferral marker or placeholder that reports success was added (U6, U20);
- [ ] every new or changed check has been seen to fail on the defect it targets (U2);
- [ ] the build, the unit tests and the touched gates pass, read by exit code (U13, U15);
- [ ] `lusser.py check` passes;
- [ ] docs changed with the code (U9);
- [ ] a behaviour promised across a family is tested once per member, and a defect has been checked
      against every sibling (U21);
- [ ] for a defect: the register row is CLOSED with its numbers, test and follow-up (U3);
- [ ] the handover is rewritten (U12).
