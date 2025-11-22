# Supabase OAuth Provider Setup Guide

This guide explains how to enable OAuth providers (Google, Apple, Microsoft) in your Supabase project.

## Quick Setup

### 1. Enable Microsoft OAuth Provider (Azure)

1. **Go to Supabase Dashboard**
   - Navigate to your project: https://app.supabase.com
   - Select your project

2. **Open Authentication Settings**
   - Go to **Authentication** → **Providers** in the left sidebar

3. **Enable Azure Provider** (Note: Supabase calls it "Azure", not "Microsoft")
   - Find **Azure** in the list of providers
   - Toggle it **ON**
   - Click **Configure**

4. **Configure Azure OAuth** (Following [Supabase Official Guide](https://supabase.com/docs/guides/auth/social-login/auth-azure))
   - **Create Azure AD Application:**
     - Go to [Azure Portal](https://portal.azure.com/)
     - Navigate to **Microsoft Entra ID** (formerly Azure Active Directory) → **App registrations**
     - Click **New registration**
     - **Name**: "Ruxo" (or your app name)
     - **Supported account types**: Choose one:
       - **Accounts in any organizational directory and personal Microsoft accounts** (recommended for most cases)
       - **Personal Microsoft accounts only** (if you only want personal accounts)
       - **My organization only** (if you only want your organization's accounts)
     - **Redirect URI**: Select **Web** platform and enter:
       - `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
       - Replace `YOUR_PROJECT_REF` with your Supabase project reference
       - Example: `https://cutgibszjdnxsrlclbos.supabase.co/auth/v1/callback`
     - Click **Register**
   
   - **Get Client ID:**
     - After registration, find your **Application (client) ID** in the app overview screen
     - Copy this value
   
   - **Create Client Secret:**
     - In your app registration, go to **Certificates & secrets**
     - Click **New client secret**
     - Add a description (e.g., "Supabase OAuth")
     - Choose an expiry time (set a reminder to rotate before expiry!)
     - Click **Add**
     - **IMPORTANT**: Copy the **Value** column immediately (you won't be able to see it again!)
     - This is your client secret
   
   - **Configure in Supabase** (Choose one method):
     
     **Method 1: Via Supabase Dashboard (Recommended for first-time setup)**
     - Go to Supabase Dashboard → **Authentication** → **Providers** → **Azure**
     - Enter:
       - **Client ID (for Microsoft Azure)**: Your Application (client) ID
       - **Client Secret (for Microsoft Azure)**: Your client secret Value
     - **Optional - Azure Tenant URL**: Only needed if:
       - Your app is registered as "Personal Microsoft accounts only" → Use `https://login.microsoftonline.com/consumers`
       - Your app is registered as "My organization only" → Use `https://login.microsoftonline.com/<your-tenant-id>`
       - Otherwise, leave blank (defaults to `https://login.microsoftonline.com/common`)
     - Click **Save**
     
     **Method 2: Via Management API (Programmatic configuration)**
     - Add to your `.env` file:
       ```env
       SUPABASE_ACCESS_TOKEN="your-access-token"
       SUPABASE_PROJECT_REF="cutgibszjdnxsrlclbos"
       AZURE_CLIENT_ID="your-azure-client-id"
       AZURE_CLIENT_SECRET="your-azure-client-secret"
       AZURE_TENANT_URL=""  # Optional, leave empty for default
       ```
     - Get `SUPABASE_ACCESS_TOKEN` from: https://supabase.com/dashboard/account/tokens
     - Run the configuration script:
       ```bash
       python backend/scripts/configure_azure_oauth.py
       ```
     - See [Supabase Management API Guide](https://supabase.com/docs/guides/auth/social-login/auth-azure#obtain-a-secret-id) for details

5. **Add Redirect URI in Azure** (CRITICAL - Must match exactly)
   - In Azure Portal, go to your app registration
   - Navigate to **Authentication**
   - Under **Redirect URIs**, ensure you have:
     - `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
     - **This is the ONLY redirect URI Azure needs** - Supabase handles the OAuth flow
     - Replace `YOUR_PROJECT_REF` with your actual Supabase project reference
     - Example: `https://cutgibszjdnxsrlclbos.supabase.co/auth/v1/callback`
   - **DO NOT add your backend or frontend URLs here** - Azure only needs Supabase's callback URL
   - Click **Save**
   - **Wait 2-3 minutes** for changes to propagate

6. **Configure Email Verification Claim (Recommended for Security)**
   - This helps prevent email domain spoofing attacks
   - In Azure Portal, go to your app registration
   - Navigate to **Manifest**
   - Make a backup of the JSON (just in case)
   - Find the `optionalClaims` key (or add it if it doesn't exist)
   - Update it to include:
     ```json
     "optionalClaims": {
         "idToken": [
             {
                 "name": "xms_edov",
                 "source": null,
                 "essential": false,
                 "additionalProperties": []
             },
             {
                 "name": "email",
                 "source": null,
                 "essential": false,
                 "additionalProperties": []
             }
         ],
         "accessToken": [
             {
                 "name": "xms_edov",
                 "source": null,
                 "essential": false,
                 "additionalProperties": []
             }
         ],
         "saml2Token": []
     }
     ```
   - Click **Save**

### 2. Enable Google OAuth Provider (Optional)

1. **In Supabase Dashboard**
   - Go to **Authentication** → **Providers**
   - Find **Google** and toggle it **ON**
   - Click **Configure**

2. **Get Google OAuth Credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
   - Copy **Client ID** and **Client Secret**

3. **Enter in Supabase**
   - Paste Client ID and Client Secret
   - Click **Save**

### 3. Enable Apple OAuth Provider (Optional)

1. **In Supabase Dashboard**
   - Go to **Authentication** → **Providers**
   - Find **Apple** and toggle it **ON**
   - Click **Configure**

2. **Get Apple OAuth Credentials**
   - Go to [Apple Developer Portal](https://developer.apple.com/)
   - Create a **Services ID** and **Key**
   - Configure redirect URLs
   - Enter credentials in Supabase

## CRITICAL: Configure Supabase Redirect URLs

**This is likely the cause of your issue!** Supabase validates redirect URLs and will block redirects that aren't in the allowed list.

1. **Go to Supabase Dashboard**
   - Navigate to your project: https://app.supabase.com
   - Select your project

2. **Configure URL Settings**
   - Go to **Authentication** → **URL Configuration**
   - Set **Site URL** to your frontend URL:
     - For local dev: `http://localhost:3000`
     - For production: Your production frontend URL
   
3. **Add Redirect URLs**
   - Under **Redirect URLs**, add:
     - `http://localhost:3000` (for local development)
     - `http://localhost:3000/` (with trailing slash)
     - `http://localhost:8000/api/v1/auth/oauth/callback` (your backend callback)
     - Your production frontend URL (if applicable)
     - Your production backend callback URL (if applicable)
   
   **Important**: Supabase will ONLY redirect to URLs in this list. If your backend callback URL or frontend URL is not listed, Supabase will block the redirect!

4. **Save Changes**
   - Click **Save** after adding all URLs

## Testing OAuth

After enabling a provider and configuring redirect URLs:

1. **Test the OAuth Flow**
   - Go to your app's login/signup page
   - Click "Continue with Microsoft" (or other provider)
   - You should be redirected to the provider's login page
   - After authentication, you'll be redirected back to your app

2. **Check Logs**
   - If errors occur, check:
     - Supabase Dashboard → **Logs** → **Auth Logs**
     - Backend logs for OAuth callback errors

## Common Issues

### "Unsupported provider" Error

**Problem**: Provider is not enabled in Supabase

**Solution**: 
- Go to Supabase Dashboard → Authentication → Providers
- Enable the provider you're trying to use
- Make sure it's properly configured with Client ID and Secret

### Redirect URI Mismatch / "Unable to exchange external code"

**Problem**: Redirect URI doesn't match what's configured in Azure, or Azure app is misconfigured

**Solution** (Following [Supabase Official Guide](https://supabase.com/docs/guides/auth/social-login/auth-azure)):
1. **Verify Azure Redirect URI** (MOST COMMON ISSUE):
   - Go to Azure Portal → **Microsoft Entra ID** → **App registrations** → Your App → **Authentication**
   - Under **Redirect URIs**, make sure you have EXACTLY:
     - `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
   - The URL must match your Supabase project URL exactly
   - Find your project reference in: Supabase Dashboard → Settings → API → Project URL
   - Example: If your Supabase URL is `https://cutgibszjdnxsrlclbos.supabase.co`, then the redirect URI must be:
     - `https://cutgibszjdnxsrlclbos.supabase.co/auth/v1/callback`
   - **Remove any other redirect URIs** (like localhost URLs) - Azure only needs Supabase's callback
   - Click **Save** and wait 2-3 minutes for changes to propagate
   
2. **Verify Azure App Configuration**:
   - **Supported account types**: Should match your use case:
     - "Accounts in any organizational directory and personal Microsoft accounts" (most common)
     - "Personal Microsoft accounts only" (if only personal accounts)
     - "My organization only" (if only your organization)
   - **Platform**: Must be set to **Web** (not Mobile/Desktop)
   - **Client ID and Secret**: Must match what's in Supabase Dashboard
   
3. **Check Supabase Configuration**:
   - Go to Supabase Dashboard → **Authentication** → **Providers** → **Azure**
   - Verify **Client ID** matches your Azure Application (client) ID exactly
   - Verify **Client Secret** matches the **Value** from Azure (not the Secret ID!)
   - Make sure Azure provider is **enabled** (toggle is ON)
   - Check **Azure Tenant URL** if you're using a specific tenant
   
4. **Verify Client Secret**:
   - Make sure you copied the **Value** column from Azure, not the **Secret ID**
   - Check if the secret has expired (go to Azure → Certificates & secrets)
   - If expired, create a new secret and update it in Supabase
   
5. **Check Email Scope**:
   - Azure requires the `email` scope (automatically included in our implementation)
   - Verify in Azure Portal → Your App → **API permissions** that email scope is available

### Being Redirected to Backend URL Instead of Frontend

**Problem**: After OAuth, you're being sent to `http://localhost:8000/api/v1/auth/oauth/callback` instead of the frontend

**Solution**:
1. **Check Supabase Redirect URLs** (MOST COMMON ISSUE):
   - Go to Supabase Dashboard → Authentication → URL Configuration
   - Make sure `http://localhost:8000/api/v1/auth/oauth/callback` is in the **Redirect URLs** list
   - Make sure `http://localhost:3000` is in the **Redirect URLs** list
   - Supabase will ONLY redirect to URLs in this list!
   
2. **Verify Backend Redirect**:
   - The backend callback should immediately redirect to the frontend
   - Check backend logs for redirect messages
   - If you see "Redirecting to frontend: ..." in logs, the redirect is happening
   
3. **Check Browser Network Tab**:
   - Open browser DevTools → Network tab
   - Look for the redirect response (302 status)
   - Verify the `Location` header points to your frontend URL

### Invalid Client Secret

**Problem**: Client secret is incorrect or expired

**Solution**:
- Generate a new client secret in Azure/Google/Apple
- Update it in Supabase Dashboard
- Make sure you're copying the **Value**, not the Secret ID

## Additional Resources

- [Supabase OAuth Documentation](https://supabase.com/docs/guides/auth/social-login)
- [Microsoft Azure AD Setup](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Google OAuth Setup](https://developers.google.com/identity/protocols/oauth2)

## Notes

- OAuth providers work for both **signup** and **login**
- If a user doesn't exist, they'll be automatically registered
- If a user already exists, they'll be logged in
- User profiles are automatically created in your database

