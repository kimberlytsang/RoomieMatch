# Contributing

## Workflow (one pull request per story)

1. Pick a story from [`docs/STORY_TRACKER.md`](docs/STORY_TRACKER.md) and put your name and "In progress" next to it.
2. Branch from `main`: `git checkout -b us-01-registration`.
3. Commit in small steps while you work. Commit messages start with the story ID: `US-01: validate duplicate email`.
4. Open a pull request into `main` using the template. Link the story and tick the checklist.
5. A teammate reviews it **in the pull request** (comments, requested changes). Reviews must be specific enough to lead to changes.
6. After approval and passing tests, merge. Paste the PR link into the tracker.

Everyone authors at least one merged PR and reviews at least one PR written by someone else.

## Definition of done (from the Sprint 3 instructions)

A story is Done only when:

- [ ] all of its acceptance criteria pass,
- [ ] a teammate reviewed it through a pull request and it is merged into `main`,
- [ ] its tests pass,
- [ ] it works in the deployed (or localhost) build.

A partly finished story stays "In progress" and returns to the product backlog.

## Tests

- At least one automated test per completed story.
- At least one test for an error, edge, or permission case from that story's acceptance criteria.
- Put tests in `tests/` named after the story, for example `tests/test_us01_registration.py`.
- Run them with `python -m pytest` before opening a PR.

## Code rules

- Keep to the layers: views handle requests and permissions, services hold business rules, models and queries are the only database access.
- Change a model? Run `python manage.py makemigrations` and commit the migration, or `test_no_pending_migrations` will fail.
- If your code departs from the Sprint 2 design, add one line to [`docs/DESIGN_CHANGES.md`](docs/DESIGN_CHANGES.md).
