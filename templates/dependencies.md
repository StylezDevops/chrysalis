# {{title}}: verified dependencies

Every package added to this project is checked against its registry before it is installed: that it
exists, who publishes it, how old it is, how widely it is used, and that it is the package meant, not a
look-alike. `hooks/block_unverified_install.py` refuses an install of a package that is neither in a
manifest nor in this table with a human's approval.

An agent may fill in the evidence. Only a human writes the approval, as `NAME (human, YYYY-MM-DD)`.

| Ecosystem | Package | Evidence | Approved |
|---|---|---|---|
