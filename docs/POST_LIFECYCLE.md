# Post Lifecycle States

This document explains the lifecycle states used for skill posts in UWA Skill-Swap.

The current lifecycle values are:

```text
open
matched
closed
```

These values describe whether a skill post is still available for new interest, has found a likely match, or is no longer active.

## Summary table

| State | Meaning | Typical user-facing wording | Should accept new interest? |
| --- | --- | --- | --- |
| `open` | The post is active and still available. | Available / Open | Yes |
| `matched` | The owner has found a likely skill-swap partner, but may still keep the post visible for context. | Matched | Usually no new interest by default |
| `closed` | The post is no longer active. | Closed / No longer available | No |

## `open`

`open` is the default active state for a skill post.

A post should be `open` when:

- the owner is still looking for a partner;
- the post should appear in normal discover results;
- other users can express interest;
- the owner may still edit, update, or close the post.

Expected UI behaviour:

- show a clear “Open” or “Available” badge;
- allow eligible users to express interest;
- include the post in ordinary discover views unless another filter excludes it.

## `matched`

`matched` means the owner has found a likely partner or has started a skill-swap conversation.

A post may be `matched` when:

- the owner has accepted or followed up with one interested user;
- the skill-swap is likely to proceed;
- the post should remain visible for dashboard/history context;
- the owner does not want the post to look fully available.

Expected UI behaviour:

- show a “Matched” badge;
- avoid presenting the post as fully available;
- future discover filtering may choose to hide matched posts by default;
- dashboard views should still show the post to the owner.

## `closed`

`closed` means the post is no longer active.

A post should be `closed` when:

- the owner no longer wants to receive interest;
- the skill-swap opportunity is finished;
- the listing was posted by mistake;
- the owner wants to keep a record without keeping the post active.

Expected UI behaviour:

- show a “Closed” or “No longer available” badge;
- do not invite new interest;
- keep the post available to the owner for history or future review;
- future discover filtering may hide closed posts by default.

## Ownership rule

Only the owner of a post should be able to change its lifecycle status.

The status update endpoint should reject:

- unauthenticated users;
- users who do not own the post;
- invalid status values;
- requests for posts that do not exist.

## Status update API expectation

The status update flow uses the following allowed values:

```json
{
  "status": "open"
}
```

```json
{
  "status": "matched"
}
```

```json
{
  "status": "closed"
}
```

A successful status update should return the updated post id and status. Invalid updates should return a clear JSON error.

## Contributor notes

When adding routes, templates, or tests that depend on post status:

- use the exact lowercase values `open`, `matched`, and `closed`;
- do not introduce new status strings without updating this document;
- keep user-facing labels clear and short;
- make sure only the post owner can update lifecycle state;
- avoid showing closed posts as available for new interest;
- document any future discover-filter behaviour that hides or shows matched/closed posts.

## Future considerations

Future PRs may add:

- status badges on all post cards;
- discover filters for active, matched, and closed posts;
- dashboard controls for status changes;
- audit text such as “Marked as matched on …”;
- confirmation prompts before closing a post.