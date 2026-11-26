# {{title}}: threat model per feature

Answered in writing for each feature that touches money, personal data or authentication (K4). The
answers go in the pull request or the story, and each "should" becomes an automated attack test.

1. What does an unauthenticated caller gain from this endpoint or action?
2. What does a logged-in user with the lowest privilege gain?
3. What happens when a parameter is missing, malformed, oversized or the wrong type?
4. What happens when the same request arrives twice?
5. What happens when a third party is down or slow?
6. What sensitive data is in the response, the logs and any error message?
7. Which recent public vulnerabilities in similar software apply, and how does this feature avoid each?

| Attack test | Expected result | Test path |
|---|---|---|
| | rejected | |
