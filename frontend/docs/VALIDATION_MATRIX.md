# Validation & UX Regression Matrix — §18

| Area | Case | Input | Expected | Status |
|---|---|---|---|---|
| Required | empty required field | `phone: ""` on Lead contacted form | `Phone is required.` inline + `400` not hit | `DynamicStageForm validate()` ✓ |
| Invalid format | bad email/phone | `lead email: "x"` | zod `email` error | `lead.schema` ✓ |
| Range | quantity 0 | `quantity:0` | `quantity ≥1` | `LineItemsEditor` ✓ |
| Date | past due_date | `due: yesterday` | `must be future` | `task.schema` ✓ |
| Duplicate | duplicate stage order | `display_order:2` duplicate | `400 unique(pipeline,display_order)` | `AdminPipelinesPage` toast ✓ |
| Workflow | progress without form | `hasRequiredForm true` but empty | block `Submit & progress` | `useWorkflowCapabilities` ✓ |
| Lock | submit on locked version | `is_locked True` | `Locked` badge + disabled `Submit` | `DynamicStageForm` ✓ |
| Permission | Employee → Mark lost without `mark_lead_lost` | `hasPermission false` | button hidden, backend `403` toast | `AppLayout` nav + `PageError` ✓ |
| 403 | view_lead without perm | `GET /leads/:id` `403` | red `You do not have permission` + `Try again` | `PageError` ✓ |
| Unsaved | leave with dirty form | `values !== {}` + nav away | prompt? (not yet) | TODO |
| Loading | slow query | `isLoading` | `PageLoader/Skeleton` | ✓ |
| Empty | no leads | `count 0` | `EmptyState` explanatory | ✓ |
