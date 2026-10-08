# Folder Organization Guide

How to organize docs into folders in Coda.

## Folder Hierarchy

```
Workspace
├── Folder
│   ├── Doc
│   ├── Doc
│   └── Subfolder
│       └── Doc
├── Folder
└── Doc (unfiled — in workspace root)
```

- Folders exist at the **workspace** level, not inside docs. They group docs, not pages.
- Do not confuse doc-internal page nesting with workspace folder structure — they are separate hierarchies.

## Folder CRUD Operations

| Operation | Tool | Notes |
|-----------|------|-------|
| List folders | `coda_list_folders` | Returns all folders accessible to the token |
| Get folder | `coda_get_folder` | Folder metadata and doc count |
| Create folder | `coda_create_folder` | Name required, optional parent folder for nesting |
| Update folder | `coda_update_folder` | Rename a folder |
| Delete folder | `coda_delete_folder` | Folder must be empty (no docs) |

## Doc-Folder Relationships

- A doc belongs to at most one folder. Unfiled docs sit in the workspace root.
- **The API cannot move a doc between folders.** `updateDoc` accepts only `title`
  and `iconName`, so `coda_update_doc` has no `folder_id` parameter. A doc's
  folder is set when it is created (`coda_create_doc`) and changed only in the
  Coda UI. Read a doc's current folder from its `folderId` via `coda_get_doc`.
- Folder membership does not affect doc permissions — sharing is doc-level.

## Folder Naming

- Use descriptive names: "Q1 2024 Planning", "Engineering", "Client Projects"
- Avoid generic names: "Misc", "Other", "Temp"
- Consistent casing: Title Case recommended
- Max folder name length: 255 characters

## Subfolder Strategy

- Subfolders (folders inside folders) are supported up to ~5 levels.
- Keep hierarchy shallow (2-3 levels max) for easy navigation.
- Pattern: `Department → Team → Project` or `Year → Quarter → Initiative`.

## Bulk Organization

The API provides no way to move an existing doc into a folder — neither in bulk
nor one at a time (see Doc-Folder Relationships above). You can create folders
(`coda_create_folder`) and create new docs inside a folder (`coda_create_doc`),
but re-filing docs that already exist is a UI-only operation.

## Folder Deletion

- `coda_delete_folder` fails if the folder contains docs. Move all docs out first.
- Deleting a folder does not delete its docs — they become unfiled.
- Deleting a parent folder requires deleting all subfolders first (leaf-to-root).

## API Constraints

- Folder IDs are stable strings (e.g., `fl-AbCdEf`).
- Folder names are not unique — two folders can have the same name.
- There is no "search folders" endpoint — list all and filter client-side.
- The API does not expose folder permissions — folder access follows workspace membership.

## Anti-Patterns

- Using folders as permission boundaries — they do not control access; doc sharing does
- Deep nesting (>3 levels) — makes navigation and API traversal difficult
- Creating a folder per doc — defeats the purpose of grouping
- Deleting folders without checking contents — will fail with an error
