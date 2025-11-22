# Frontend Environment Variables

Copy this file to `.env.local` and fill in your values:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_V1_URL=http://localhost:8000/api/v1
```

## Setup Instructions

1. Copy this file to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Fill in your Supabase credentials:
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anon/public key (from Supabase Dashboard > Settings > API)

3. Update backend URL if different from default:
   - `NEXT_PUBLIC_API_URL`: Your backend base URL
   - `NEXT_PUBLIC_API_V1_URL`: Your backend API v1 URL

## Notes

- All `NEXT_PUBLIC_*` variables are exposed to the browser
- Never commit `.env.local` to version control
- Restart your Next.js dev server after changing environment variables

