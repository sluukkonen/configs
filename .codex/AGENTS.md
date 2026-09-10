## Implementation completion

For implementation tasks, do not stop immediately after making the requested
change.

Before completion:

- review the complete diff against the requested behavior;
- inspect for correctness bugs, regressions, edge cases, and missing error paths;
- fix material issues you discover;
- run relevant tests, linters, and type checks;
- review the resulting diff again after fixes.

For each discovered bug, check the affected code for other instances of the
same underlying failure pattern.

Do not churn on purely stylistic or speculative findings. Finish when the
requested behavior is implemented, relevant checks pass, and a fresh inspection
of the final diff reveals no material issues.
