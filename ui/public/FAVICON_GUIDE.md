# Favicon Setup Guide

This guide explains how to generate the required icon files for the Ruxo application.

## Required Icon Files

The following icon files need to be generated from the logo SVG (`/public/images/logo.svg`):

1. **favicon.ico** - Already exists, should contain multiple sizes (16x16, 32x32, 48x48)
2. **icon-16x16.png** - 16x16 PNG icon
3. **icon-32x32.png** - 32x32 PNG icon
4. **icon-192x192.png** - 192x192 PNG icon (for Android)
5. **icon-512x512.png** - 512x512 PNG icon (for Android)
6. **apple-touch-icon.png** - 180x180 PNG icon (for iOS)

## How to Generate Icons

### Option 1: Using Online Tools
1. Visit https://realfavicongenerator.net/ or https://favicon.io/favicon-converter/
2. Upload the logo SVG (`/public/images/logo.svg`)
3. Configure settings:
   - iOS: Enable Apple touch icon (180x180)
   - Android: Enable Android icons (192x192, 512x512)
   - Windows: Enable Windows tiles
4. Download and extract all generated files to `/public/`

### Option 2: Using ImageMagick or Similar
```bash
# Install ImageMagick (if not already installed)
# Then convert the logo SVG to various sizes:

convert public/images/logo.svg -resize 16x16 public/icon-16x16.png
convert public/images/logo.svg -resize 32x32 public/icon-32x32.png
convert public/images/logo.svg -resize 192x192 public/icon-192x192.png
convert public/images/logo.svg -resize 512x512 public/icon-512x512.png
convert public/images/logo.svg -resize 180x180 public/apple-touch-icon.png

# For favicon.ico (multi-size ICO file)
convert public/images/logo.svg -resize 16x16 -resize 32x32 -resize 48x48 public/favicon.ico
```

### Option 3: Using Node.js Script
You can create a script using `sharp` or `jimp` to convert the SVG to all required sizes.

## Files Already Configured

- ✅ `site.webmanifest` - Web app manifest file
- ✅ `safari-pinned-tab.svg` - Safari pinned tab icon
- ✅ `layout.tsx` - Metadata configuration with all icon links

## Testing

After generating the icons, test the favicon on:
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (iOS Safari, Android Chrome)
- Check browser tabs, bookmarks, and home screen icons

## Notes

- The theme color is set to `#cefb16` (Ruxo green)
- All icons should use the Ruxo logo design
- Ensure icons have transparent backgrounds where appropriate
- Apple touch icon should have padding (180x180 with logo centered)

