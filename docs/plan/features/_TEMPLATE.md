# Feature: <name>

> One-paragraph plain-language description of what this feature is and why it
> exists. A stranger should understand this section without reading the rest.

## Scope

**In scope:**
- (bullet list of what this feature DOES include)

**Out of scope:**
- (bullet list of what this feature does NOT include — explicit non-goals
  protect against scope creep within the feature chat)

## Depends on

- (Other features that must be done first. If none, write "Nothing — this is
  foundational.")

## Touches

What parts of the codebase this feature creates or modifies. Be specific.

- **Backend models:** (e.g. `apps/catalog/models.py` — new `Product` model)
- **Backend endpoints:** (e.g. `GET /api/products`)
- **Backend admin:** (e.g. register Product in Django admin)
- **Frontend components:** (e.g. `sections/MerchSection.jsx`, `components/MerchCard.jsx`)
- **Frontend API calls:** (e.g. `lib/api.js` — add `fetchProducts()`)
- **Database migrations:** (yes/no, what's added)
- **Environment variables:** (any new ones needed)
- **Third-party integrations:** (Stripe, Resend, etc.)

## Behavior

The actual logic. Use plain-language step-by-step where it helps, code-level
detail where it's needed for unambiguous implementation. Cover:

1. The happy path
2. The error paths
3. The edge cases worth naming explicitly

Avoid pseudocode for things the implementer will obviously do (don't write
"open a connection to the database"). Do write code-level detail for
non-obvious flows (e.g., the exact shape of a Stripe webhook handler).

## Data shape (if relevant)

If this feature defines or returns a particular JSON shape, show it:

```json
{
  "example": "of what the API returns"
}
```

If this feature defines a new database model, show the field list and
constraints (not full Django syntax — that's for the implementation):

```
Product
- id (auto)
- slug (unique, indexed)
- name (string)
- ...
```

## Definition of done

A checklist a feature chat can self-grade against. If every box is checked,
this feature is mergeable. If any box is unchecked, it's not done.

- [ ] (specific, verifiable outcome — not "works correctly")
- [ ] (specific, verifiable outcome)
- [ ] Tests where relevant (see "Testing" below)
- [ ] Manually verified end-to-end in dev
- [ ] No new linter warnings introduced
- [ ] Feature docs updated if anything was learned that changes the plan

## Testing

What's worth testing for this feature? Not everything needs unit tests, but
some things do:

- **Always worth a test:** money math, stock decrement, Stripe webhook signature
  verification, anything with branching logic
- **Worth a test if non-trivial:** API endpoint shape, model methods
- **Not worth a unit test:** UI components (manual verification is fine for v1),
  thin Django views that just serialize a queryset

## Open questions

If anything's unresolved when the feature chat opens this file, list it here.
The feature chat should NOT silently invent answers to open questions; it
should either ask in chat or punt back to the plan chat.

- (open question 1)
- (open question 2)

## Notes for the feature chat

(Free-form. Things that are useful context but don't fit above. Sources,
relevant docs, gotchas the plan chat noticed.)
