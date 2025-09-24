# PayloadCMS Storage and Uploads Configuration

## Overview

This document covers how to configure PayloadCMS with Cloudflare R2 (S3-compatible storage) and implement file uploads using local forms.

## Cloudflare R2 Configuration

### 1. Install Required Dependencies

```bash
npm install @aws-sdk/client-s3 @payloadcms/plugin-cloud-storage
```

### 2. Environment Variables

Add these to your `.env` file:

```env
# Cloudflare R2 Configuration
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
CLOUDFLARE_R2_REGION=auto
CLOUDFLARE_R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
CLOUDFLARE_R2_PUBLIC_URL=https://your_custom_domain.com
```

### 3. PayloadCMS Configuration

```typescript
// payload.config.ts
import { buildConfig } from 'payload/config'
import { s3Storage } from '@payloadcms/storage-s3'

// Configure Cloudflare R2 storage adapter
const s3Adapter = s3Storage({
  config: {
    endpoint: process.env.CLOUDFLARE_R2_ENDPOINT,
    region: 'auto', // Required for Cloudflare R2
    credentials: {
      accessKeyId: process.env.CLOUDFLARE_R2_ACCESS_KEY_ID!,
      secretAccessKey: process.env.CLOUDFLARE_R2_SECRET_ACCESS_KEY!,
    },
    forcePathStyle: true, // Required for R2
  },
  bucket: process.env.CLOUDFLARE_R2_BUCKET_NAME!,
  collections: {
    media: {
      prefix: 'media', // Optional: organize files in a folder
      generateFileURL: ({ filename }) => {
        // Generate the public URL using the custom domain
        const baseUrl = process.env.CLOUDFLARE_R2_PUBLIC_URL || 'https://media.rumbletv.com'
        return `${baseUrl}/media/${filename}`
      },
    },
  },
})

export default buildConfig({
  plugins: [s3Adapter],
  ...
```

This configuration provides a solid foundation for handling file uploads in PayloadCMS with Cloudflare R2 storage and local form uploads.