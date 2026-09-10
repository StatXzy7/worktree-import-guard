# Security

worktree-import-guard diagnoses selected imports in the current pytest process. It is not a
sandbox, environment repair tool, or proof that code matches a commit. Pytest executes project
code; hostile code in the same process may interfere with observation.

For non-sensitive bugs, use [GitHub issues](https://github.com/StatXzy7/worktree-import-guard/issues).
Do not post credentials, private source, full environment variables or sensitive paths. Reports
and arguments may contain usernames and company directories; redact them first.

A private reporting channel has not been verified or established for this candidate. No security
email is promised here. If private details are needed, post only a request for a private contact,
without sensitive content, and wait for the maintainer to arrange a channel.

Before release, the maintainer should configure and verify a private reporting channel and update
this document with the actual link. 0.1.0 is a candidate; no released-version support window is
claimed yet.
