# Admin UI — History

## 1. Admin UI Goals
- **Purpose**: Headless CMS for site content + compliance config builder
- **Scope**: Pages, articles, media, jurisdiction configs (KYC/AML), field definitions
- **Principle**: Next.js API routes proxy to FastAPI backend (separation of concerns)
- **Auth**: Session-based (Next.js cookies), JWT tokens generated server-side for FastAPI calls

## 2. Key Design Decisions
- **Framework**: Next.js 14+ App Router (server components + client components)
- **UI Library**: shadcn/ui (Radix UI primitives + Tailwind CSS)
- **State**: React hooks (useState, useEffect), no global state manager
- **API Pattern**: Next.js route handlers (`/api/admin/*`) proxy to FastAPI (`/api/*`)
- **Layout**: Fixed sidebar (`AdminSidebar`) + main content area (flex layout)
- **Error Handling**: Toast notifications (`toastSuccess`, `toastError` from `@/lib/admin/toast`)

## 3. API Contracts Used
- **Next.js API Routes** (proxy layer):
  - `/api/admin/jurisdiction-configs` → `GET` (list), `POST` (create)
  - `/api/admin/jurisdiction-configs/[id]` → `GET`, `PUT`
  - `/api/admin/jurisdiction-configs/[id]/publish` → `POST`
  - `/api/admin/field-definitions` → `GET` (list with filters)
- **FastAPI Backend** (via proxy):
  - `/api/jurisdiction-configs` (FastAPI routes)
  - `/api/field-definitions` (FastAPI routes)
- **Auth**: `getSessionFromCookie()` → generates JWT token → `Authorization: Bearer {token}`
- **Env Var**: `API_BASE_URL` (default: `http://localhost:8000`)

## 4. Known UI Pitfalls
- **Select Component** (shadcn/ui):
  - Issue: `SelectItem` cannot have `value=""` (empty string)
  - Fix: Use sentinel value `__all__` for "All" options, map to `''` in state
  - Files affected: `jurisdiction-configs/page.tsx`, `FieldSelector.tsx`
- **Proxy Routes**:
  - Issue: Wrong API base URL (8011 vs 8000), missing JWT auth
  - Fix: Use `API_BASE_URL` env var, generate JWT tokens in route handlers
  - Files fixed (2025-01-12): All `/api/admin/jurisdiction-configs/*` routes, `/api/admin/field-definitions/route.ts`
- **Layout**:
  - Issue: Missing `admin/layout.tsx` caused 404 for `app/admin/layout.js`
  - Fix: Created layout with `AdminSidebar` + flex container
  - Pattern: Login page excluded from layout, all other admin pages wrapped
- **Error Display**:
  - Issue: Infinite "Chargement..." on fetch errors
  - Fix: Added error state + retry button in list pages
- **Fetch URLs**:
  - Issue: Frontend called `/admin/jurisdiction-configs` instead of `/api/admin/jurisdiction-configs`
  - Fix: Updated all fetch calls to use Next.js API proxy routes

## 5. UX Improvements Deferred
- **Drag/Drop Persistence**: KYC builder drag/drop exists but order not persisted to backend
- **Loading States**: Skeleton loaders missing (only "Chargement..." text)
- **Error Messages**: Generic errors, no field-level validation feedback
- **Form Validation**: Client-side validation missing (relies on backend errors)
- **Auto-save**: No draft auto-save for jurisdiction configs
- **Undo/Redo**: No history for config edits
- **Preview Mode**: Onboarding preview renders but cannot submit (by design)
- **Bulk Operations**: No bulk edit/delete for configs
- **Search/Filter UX**: Basic filters exist, no advanced search (date ranges, tags)
- **Mobile Responsive**: Admin UI not optimized for mobile (sidebar fixed width)
