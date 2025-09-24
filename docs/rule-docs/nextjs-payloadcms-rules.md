# Next.js 15.4+ & Payload CMS 3.56+ Rules
**important** do not use patterns that are not for payloadcms version 3.4 or higher.

## Project-Specific Context
- **Payload CMS Version**: 3.56.0 (with MongoDB adapter)
- **Next.js Version**: 15.4.4
- **Database**: MongoDB via `@payloadcms/db-mongodb`
- **Development Server**: Runs on localhost:3005
- **Scripts**: Uses VisionCraft mcp CLI tool instead of Drush commands

## Payload CMS (v3.56+)
- **Imports**: `import type { CollectionConfig } from 'payload'`
- **Types**: Run `pnpm generate:types` after schema changes. NEVER edit generated types.
- **Local API**: Use `getPayload({ config })` in server components, not REST API
- **Scripts**: Use `cross-env NODE_OPTIONS=--no-deprecation payload script.js`
- **Config**: Payload config located at `./src/payload.config.ts` with import path `@payload-config`
- **Collections**: Custom collections in `./src/collections/` directory
- **Database**: MongoDB adapter configured with environment variable `DATABASE_URI`

## Next.js 15.4+ (App Router)
- **Server Components**: Default. DON'T add `'use client'` unless needed for browser APIs, events, or hooks
- **Client Components**: ONLY for useState, useEffect, onClick, browser APIs
- **Data Fetching**: Use Payload local API in server components
- **File Structure**: `app/` for pages, `collections/` for Payload, `components/` for reusable

## Critical Patterns
```typescript
// Payload Config Import (Project-specific)
import config from '@payload-config'

// Payload in Server Component
import { getPayload } from 'payload'
const payload = await getPayload({ config })

// Collection Configuration
import type { CollectionConfig } from 'payload'
export const CollectionName: CollectionConfig = {
  slug: 'collection-slug',
  fields: [...],
  access: {...}
}

// Client Component (only when needed)
'use client'
import { useState } from 'react'
```


## Don't
- Use `'use client'` unnecessarily
- Edit generated Payload types
- Use REST API when local API available
- Forget to regenerate types after schema changes
- Use VisionCraft mcp CLI tool for entity updates (not Drush)
- Deploy without manual instructions (no automated scripts)