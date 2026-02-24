Audit sharing and permissions for Coda doc `{doc_id}`.

## Steps

1. **List current permissions** — use `coda_list_permissions` with doc_id="{doc_id}". For each ACL entry, note:
   - Principal type (email, domain, anyone)
   - Access level (readonly, comment, write)
   - Whether it was inherited or directly assigned
2. **Check for public access** — look for `principal.type: "anyone"`:
   - If present, evaluate whether public access is intentional
   - Flag any `anyone` + `write` entries as high-risk
3. **Check domain sharing** — look for `principal.type: "domain"`:
   - Verify the domain is appropriate (company domain vs. public domain like gmail.com)
   - Flag broad domain sharing on sensitive docs
4. **Review individual access** — for `principal.type: "email"`:
   - Identify users with write access who may only need read
   - Flag external email addresses (outside the organization's domain)
   - Look for stale entries (users who may have left the organization)
5. **Check page locks** — use `coda_list_pages` and review lock settings:
   - Are sensitive pages locked to prevent accidental edits?
   - Are locks appropriate (not too restrictive, not too permissive)?
6. **Summarize findings**:
   - Total ACL entries by type and access level
   - Risk assessment: high (public write), medium (broad domain), low (individual read)
   - Recommendations: entries to remove, access levels to downgrade, pages to lock
7. **Suggest tightening**:
   - Convert `anyone` to domain-level where possible
   - Downgrade `write` to `readonly` for view-only users
   - Add page locks to sensitive content pages