# Story tracker

Update this file in the same PR that changes a story's status. Status is To do, In progress, or Done. A story is Done only when it meets the definition of done in CONTRIBUTING.md.

## Sprint backlog (chosen stories)

**Sprint goal:** Users can create a RoomieMatch account, log in, log out, and search for roommates.

| Story | Owner | Estimate | Status | Pull requests / commits | Acceptance criteria changed? (reason) |
|---|---|---|---|---|---|
| US-01 Registering an account | Kimberly | 2 | Completed | https://github.com/kimberlytsang/RoomieMatch/pull/1 | Yes: password requirements were specified, with specific validation messages; duplicate-email wording was clarified to `An account with this email already exists.`. |
| US-02 Log in | Kimberly | 3 | Completed | https://github.com/kimberlytsang/RoomieMatch/pull/1 | No changes. |
| US-03 Log out | Kimberly | 1 | Completed | https://github.com/kimberlytsang/RoomieMatch/pull/1 | No changes. |
| US-07 Search for potential roommates | Joyce | TBD | Completed | https://github.com/kimberlytsang/RoomieMatch/pull/2 | No changes. |
| US-12 Filter roommate search results | Joyce | TBD | Completed | https://github.com/kimberlytsang/RoomieMatch/pull/2 | No changes. |
| US-13 Change password | Kimberly | 2 | Awaiting review | https://github.com/kimberlytsang/RoomieMatch/pull/3 | No changes. |

These stories remain In progress until reviewed and merged, their acceptance criteria pass, tests pass, and they work in the deployed or localhost build.

## Product backlog (pending stories, in priority order)

| Priority | Story | Level | Estimate | Notes |
|---|---|---|---|---|
| | US-04 Budget preference | MVP | | |
| | US-05 Location preference | MVP | | |
| | US-06 Lifestyle preference | MVP | | |
| | US-07 Search for potential roommates | MVP | | |
| | US-08 View another user's profile | MVP | | |
| | US-09 Send a message | MVP | | |
| | US-10 User session management | MVP | | |
| | US-11 View conversations | MVP | | |
| | US-14 Delete account | MVP | | |
| | US-15 Create and manage user profile | MVP | | |
| | US-16 Create a group | Stretch | | |
| | US-17 Personalized roommate matching | Out of scope | | Machine learning is out of scope |
| | US-18 User support form | MVP | | |
| | US-19 View user support requests | MVP | | |
| | US-20 Update user support request status | MVP | | |

## Changes since Sprint 1 (added, split, merged, or dropped)

| Story | Change | One-line reason |
|---|---|---|
| US-19, US-20 | Added | Administrator needs to view support requests and update their status |
