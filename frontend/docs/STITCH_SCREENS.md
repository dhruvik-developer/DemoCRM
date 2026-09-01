# Stitch Screens — DemoCRM Sales Workspace

> Generated via Stitch MCP (`stitch.googleapis.com/mcp`) — project `9677310215816547351` `DemoCRM - Sales Workspace` / design system `71ffd25e0c824de689527dce468a0f8d` (Geist, `#2563EB`, 8px rhythm). Stack mirrors `package.json` (Vite 8.2 + React 19 + TanStack Query + RHF+Zod + shadcn radix-nova neutral).

## Project
- **Project:** `projects/9677310215816547351` — `DemoCRM - Sales Workspace` (`PROJECT_DESIGN`, PRIVATE)
- **Design system:** `assets/71ffd25e0c824de689527dce468a0f8d` — source screen `4002891570990188774` (DESIGN.md upload), `apply_design_system` ready
- **Config:** `~/.config/opencode/opencode.jsonc` → `mcp.servers.stitch` `remote` `https://stitch.googleapis.com/mcp` `oauth:false` `headers.X-Goog-Api-Key = AQ.Ab8...` (inline after `STITCH_API_KEY` env), verified `✓ stitch connected`
- **Theme:** body/headline/label `GEIST`, light fidelity, `overridePrimary #2563eb`, `overrideNeutral #6b7280`, spacing sidebar 240 / topbar 56 / row 44 / input 36

## Screens — download & use
> `htmlCode.downloadUrl` is `contribution.usercontent.google.com` (requires auth cookie). Click or `curl -L -H "Authorization: Bearer …"` to save. `screenshot.downloadUrl` (`lh3.googleusercontent.com/aida`) is public preview. All prompts use design system `assets/71ff...`.

### 1. Sales Workspace — Lead Workspace: Acme Industries `348bff08edc24cf19487894ed72134b9`
Lead Header (Acme Industries · Raj Patel · ACTIVE) → PipelineStepper [Initial Contact]→[Qualification]→**[Proposal* active #2563EB]**→[Negotiation]→[Won] → 2 cards Lead Information (Sarah Jenkins/LinkedIn/$50k) + Current Task (Follow-up Call High Tomorrow) → Current Stage Form (Proposal Title/Select/Date) sticky `Save draft` / `Submit & progress` → Form Response History 27 Aug v2 field→answer → Activity/Call timeline vertical + Quotation Required panel placeholder.
- HTML: `projects/9677310215816547351/files/a66c4e0f425d41efa83a6c4e683716a5`
- Screenshot: `projects/.../files/2dea1290d4474dc4ba59b3bc3b2b03ce` (2730px)
- Maps to: `src/features/sales` + `src/components/sales/*` + `workflow/PipelineStepper`, `layouts/AppLayout` CRM Sales shell, `features/callforms/components/DynamicFormFields.jsx` + `dynamicFormValidate.js`, `features/activities/components/ActivitiesCard.jsx`, `features/quotations/components/QuotationPanel`

### 2. Leads List `a1f13ec9420b4bd294362ac7eb58a24f`
Header Leads + `Create Lead` primary → Filters Search/Status/Pipeline/Stage/Owner + Clear → DataTable 44px Lead+Company / Stage badge / Status ACTIVE `#E0F2FE` / Owner avatar / Source / Next Task / Updated / chevron + pagination, sticky header `#F9FAFB`, empty/loading states.
- HTML: `projects/.../files/5fca76d1b4cd4ea481a0b9aa1eab8740`
- Screenshot: `projects/.../files/6bdcf3104ff5435b8960ea1b25950c46`
- Maps to: `src/features/leads/pages/LeadsListPage.jsx` (URL-synced `?search=&status=&pipeline=&current_stage=&assigned_to=&ordering=&page=`) + `DataTable.jsx` + `StatusBadge.jsx` + `features/crm/hooks useLeadSources/usePipelines/usePipelineStages` (resolves source/pipeline names, backend only returns FK ids). Do not invent `/users` (G6 manual UUID fallback).

### 3. My Tasks Inbox `fd8e207857a74582a6b06c9901ed5320`
Header My Tasks + tabs [All][Overdue][Today][Upcoming] → inbox cards with left blue accent for High: `Call Acme Industries High Due 2:00 PM — Raj Patel · Proposal →` / `Bright Systems Medium Tomorrow` → priority badge + due + lead + stage, chevron opens Sales Workspace. Style white border hover `#F9FAFB` radius 12.
- HTML: `projects/.../files/69c7c9c854b64eb498101bce611ecbbe`
- Screenshot: `projects/.../files/f15fc8d07d3a4192a88716de89b0a6fa`
- Maps to: `src/features/tasks/pages/TasksListPage.jsx` (filters `?status=&priority=&category=&assigned_to=`; Employee sees only `assigned_to=request.user` per backend) → click `→ /leads/:leadId` workspace, not generic detail (`PHASE 10.4`). Master data hardcodes `src/utils/taskMasterData.js` (G7).

### 4. Quotation Detail Q-1024 `2bee4be10fc64532960b605c95e24def`
Header `Q-1024 Draft · ₹5,40,000` → LineItemsEditor table Description/Qty/Unit Price/Amount + Add Item → Totals Subtotal/Tax/Grand Total → vertical approval timeline Created→Pending→Send→Accept/Reject → sticky `Submit for Approval` / `Save Draft` / Delete.
- HTML: `projects/.../files/77f2de6a88c6495aa40d5a531b925861`
- Screenshot: `projects/.../files/cd421a3875d34ad593725206119d316e`
- Maps to: `src/features/quotations/pages/QuotationDetailPage.jsx` (11 hooks `useQuotation/create/updateDraft/submit/approve/...` + `LineItemsEditor.jsx` quantity≥1 unit_price≥0.01 total `sum(qty*price)`) + `features/quotations/api.js` lifecycle; destructive confirm dialogs + self-approval 403 handling; embedded in Proposal quotation-required stage via `QuotationPanel`.

## Code File Connections — Business Trace
`main.jsx` → `App.jsx` (AuthProvider) → `router/index.jsx` (`ProtectedRoute`→`AppLayout` nav filter via `hasPermission(resolved)`) → pages. `useAuth` → `tokenStorage` + `axios` (Bearer+401 refresh race guard + `normalizeApiError`) + `jwt` + `permissions` + `auth/api` (profile nested `data.profile`). `endpoints.js` suffix-only map (verified `/schema/` 2026-08-26) → `features/*/api.js` → `hooks.js` (TanStack `queryKeys.*`) → `pages/*` (RHF+Zod `schemas/*` → `FormField`+ui) → `common/StatusBadge/EmptyState` + `tables/DataTable` + cross-feature invalidation (lead progress→leads+customers, quotation accept→convert). `callforms` → `lead-primary-form?lead_id=` → `DynamicFormFields` → submit → `triggerRules` → auto Task/Reminder. `activities` embedded in Lead/Customer detail (`?lead=`). `docs/*.md` are contracts driving gaps G6–G23.

## How to use
1. Open each HTML locally or re-import to Figma via Stitch download. Assets already match `src/index.css` `oklch` tokens and `src/components/ui/*` (button/card/badge/table/dialog).
2. Apply design system to new screens: `stitch_apply_design_system({ assetId:"71ffd...", projectId:"967731...", selectedScreenInstances:[...] })`.
3. Edit screens: `stitch_edit_screens({ projectId:"967731...", selectedScreenIds:["348bff..."], prompt:"..." })`.
4. Wire to `AppLayout` CRM Sales IA (`CRM_FRONTEND_AGENT_MASTER_PROMPT.md` §4): see `src/layouts/AppLayout.jsx` change below.

## Regen
```sh
opencode2 mcp list
# then: stitch_create_project / upload_design_md (ascii base64) / create_design_system_from_design_md / generate_screen_from_text {projectId, designSystem:"assets/71ff...", deviceType:"DESKTOP", prompt}
```
