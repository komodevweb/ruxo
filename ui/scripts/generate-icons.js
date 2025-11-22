const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const inputFile = path.join(__dirname, '../public/image-6c2dc247.png');
const outputDir = path.join(__dirname, '../public');

// Icon sizes to generate
const iconSizes = [
  { name: 'icon-16x16.png', size: 16 },
  { name: 'icon-32x32.png', size: 32 },
  { name: 'icon-192x192.png', size: 192 },
  { name: 'icon-512x512.png', size: 512 },
  { name: 'apple-touch-icon.png', size: 180 },
];

async function generateIcons() {
  console.log('Starting icon generation...');
  console.log(`Input file: ${inputFile}`);
  
  // Check if input file exists
  if (!fs.existsSync(inputFile)) {
    console.error(`Error: Input file not found: ${inputFile}`);
    process.exit(1);
  }

  try {
    // Generate each icon size
    for (const icon of iconSizes) {
      const outputPath = path.join(outputDir, icon.name);
      console.log(`Generating ${icon.name} (${icon.size}x${icon.size})...`);
      
      await sharp(inputFile)
        .resize(icon.size, icon.size, {
          fit: 'cover', // Cover ensures exact size, fills the entire canvas
          background: { r: 0, g: 0, b: 0, alpha: 0 } // Transparent background
        })
        .png({ quality: 100 })
        .toFile(outputPath);
      
      console.log(`✓ Created ${icon.name}`);
    }

    // Also create/update favicon.ico (using the 32x32 version)
    const faviconPath = path.join(outputDir, 'favicon.ico');
    console.log('Generating favicon.ico...');
    
    // Create a multi-size ICO file
    // For simplicity, we'll use the 32x32 version for favicon.ico
    await sharp(inputFile)
      .resize(32, 32, {
        fit: 'cover', // Cover ensures exact size
        background: { r: 0, g: 0, b: 0, alpha: 0 }
      })
      .png({ quality: 100 })
      .toFile(faviconPath);
    
    console.log(`✓ Updated favicon.ico`);
    console.log('\n✅ Icon generation complete!');
    
  } catch (error) {
    console.error('Error generating icons:', error);
    process.exit(1);
  }
}

generateIcons();

