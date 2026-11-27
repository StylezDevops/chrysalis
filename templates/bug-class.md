# {{title}}: bug classes

Patterns that have caused a defect here and are likely to recur (U3). One entry per class. When a
new defect matches a class, add the register row to the entry and hunt the class across the code.

## BC-1: name of the class

| | |
|---|---|
| Risk on this stack | Critical / High / Moderate, and why |
| First seen | register row, date |
| How to search for it | the grep, query or analyser rule that finds candidates |
| Check that catches it | the test, gate or hook, or "none yet" |

Wrong:

```
the shape of the defect, as small as possible
```

Right:

```
the corrected shape
```

Sites cleared in the last hunt, with date:
