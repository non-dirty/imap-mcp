# Commit Message Conventions

This document outlines the commit message format and conventions for the IMAP MCP project.

## Format

All commit messages should follow this format:

```
type(scope): short description

[optional body]

[optional footer]
```

## Type

The type must be one of the following:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Changes that do not affect the meaning of the code (formatting, etc.)
- `refactor`: Code changes that neither fix a bug nor add a feature
- `test`: Adding or correcting tests
- `chore`: Changes to the build process, tools, etc.

## Scope

The scope should be the name of the module affected (e.g., `auth`, `imap`, `cli`).

## Issue References

For commits related to GitHub issues, use one of these formats:

- `fix(auth): implement token refresh (fixes #42)`
- `feat(imap): add folder listing capability (closes #123)`
- `test(auth): add tests for OAuth flow (refs #56)`

## Examples

```
feat(oauth): implement Gmail OAuth2 flow

- Add authorization URL generation
- Add token exchange process
- Add refresh token handling

Closes #21
```

```
fix(parser): handle empty IMAP response correctly

Previously empty responses would cause a KeyError. This fix adds proper
checking for empty responses.

Fixes #45
```

```
test(coverage): improve test coverage for IMAP client

Added tests for connection errors and timeouts. Coverage now at 95%.

Refs #22
```

## Pull Requests

When creating pull requests:

1. Reference related issues in the PR description
2. Use the provided PR template
3. Ensure that the commits follow these conventions
4. Squash commits when appropriate for a cleaner history

Following these conventions helps with:
- Automatic issue tracking
- Generating meaningful changelogs
- Making the project history navigable and useful
