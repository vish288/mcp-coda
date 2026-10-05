# Coda Permission Model

Rules for sharing, access control, and permission management in Coda.

## Permission Hierarchy

```
Organization
└── Doc
    ├── Doc-level sharing (primary ACL)
    ├── Page-level locking (restrict editing, not viewing)
    └── Table/row-level (conditional via formulas, not API-enforced)
```

Permissions flow **top-down**: a doc's sharing settings determine who can access it. Page-level controls only restrict editing, not viewing.

## Principal Types

| Type | API `principal.type` | Description |
|------|---------------------|-------------|
| `email` | `email` | Individual user by email address |
| `domain` | `domain` | All users in an email domain (e.g., `@company.com`) |
| `anyone` | `anyone` | Public link — no authentication required |

## Access Levels

| Level | `access` value | Capabilities |
|-------|---------------|--------------|
| Read only | `readonly` | View content, cannot edit |
| Can comment | `comment` | View + add comments |
| Can edit | `write` | Full edit access to unlocked pages |
| Owner | N/A (creator) | Edit + manage sharing + delete doc |

- Only doc **owners** can manage permissions via API.
- The API token's permissions are the ceiling — you cannot grant more access than the token holder has.

## Sharing Operations

- `coda_list_permissions` — list all ACL entries for a doc
- `coda_add_permission` — grant access to a principal
- `coda_delete_permission` — revoke a specific ACL entry by permission ID
- `coda_search_principals` — find users/domains for permission assignment

## Page Locking

- Page locking is a Coda UI feature. The REST API does not read or set it — the page object carries no lock field, and `coda_update_page` has no lock parameter.
- Locked pages are still **viewable** by anyone with doc access.
- Page locking is not a security boundary — it only prevents accidental edits.
- To control editing programmatically, use doc-level sharing (`coda_add_permission`), not page locks.

## Domain Sharing

- Domain sharing (`principal.type: "domain"`) grants access to all users with that email domain.
- Use for org-wide docs. Avoid for sensitive content — any new user with that domain auto-gets access.
- Domain + `readonly` is the safest default for internal knowledge bases.

## API Constraints

- Permission changes require doc owner access. Editor-level tokens cannot modify ACLs.
- `coda_add_permission` emails the user by default. Pass `suppress_notification=True` to skip the email.
- Removing the last owner is not allowed — the API will reject it.
- Permission IDs are opaque strings. Always list permissions first to get IDs for deletion.

## Anti-Patterns

- Relying on page locking as a security boundary — it only prevents editing, not viewing
- Using `anyone` access for internal docs — prefer domain-level sharing
- Granting `write` access broadly then locking individual pages — complex and error-prone
- Not checking current permissions before adding — duplicates are silently created
