---
name: commit
description: Review current Git changes and create appropriately scoped, atomic commits with detailed rationale-rich messages.
---

# Commit Changes

Use this skill when the user asks to commit current repository changes.

## Model choice

Keep this routine workflow efficient:

- Prefer Luna with `low` or `none` reasoning for ordinary commits.
- Use Sol with `low` or `medium` reasoning when the diff is broad, ambiguous, or requires more careful review.
- Use Astra only for unusually complex, high-risk, or difficult-to-validate changes, with `low` or `medium` reasoning. Do not use Astra at `max` for ordinary commits.
- If the active session model cannot be changed by the skill, continue with it and avoid unnecessary analysis or tool calls.

## Workflow

1. Inspect `git status --short`, the staged and unstaged diffs, and recent commit messages.
2. Preserve existing staging choices where possible. Do not include unrelated changes or files that appear staged for another purpose.
3. If there is nothing to commit, report that and stop.
4. Review the changes for obvious mistakes, secrets, generated artifacts, and accidental files. If a material problem is found, explain it and stop before committing.
5. Partition independent logical changes into a set of atomic commits when applicable. Keep inseparable changes together; do not split one logical change just to increase the commit count.
6. Run the quickest relevant validation for each affected area. Skip expensive or unrelated checks. If validation indicates the changes should not be committed, report the failure and stop.
7. Create each commit with a sufficiently detailed message:
   - Use a concise imperative subject.
   - For non-trivial changes, add a body explaining what changed and, especially, why it is necessary, including relevant constraints or trade-offs.
   - Keep each message accurate to its atomic commit and follow the repository's existing convention when apparent.
8. Stage only the intended changes for the current commit and create the planned commit(s). Never amend an existing commit, force-push, reset, clean, or discard changes.
9. Verify every new commit with `git show --stat --oneline --summary <commit>` and verify the final state with `git status --short`.

If the user provides additional commit-message or scope guidance, apply it while preserving these safety and atomicity rules.

Report each commit's hash and message, the files summarized, validation performed, and any remaining working-tree changes.
