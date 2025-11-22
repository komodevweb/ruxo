const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const sourceDir = path.join(__dirname, '../public/images/home');
const files = fs.readdirSync(sourceDir);

async function convertToWebP() {
  const converted = [];
  
  for (const file of files) {
    // Skip if already webp or not an image
    if (file.endsWith('.webp') || (!file.endsWith('.jpg') && !file.endsWith('.jpeg') && !file.endsWith('.png'))) {
      continue;
    }
    
    const inputPath = path.join(sourceDir, file);
    const outputPath = path.join(sourceDir, file.replace(/\.(jpg|jpeg|png)$/i, '.webp'));
    
    try {
      await sharp(inputPath)
        .webp({ quality: 85 })
        .toFile(outputPath);
      
      converted.push({
        original: file,
        webp: path.basename(outputPath)
      });
      
      console.log(`✓ Converted: ${file} → ${path.basename(outputPath)}`);
    } catch (error) {
      console.error(`✗ Failed to convert ${file}:`, error.message);
    }
  }
  
  console.log(`\n✅ Conversion complete! Converted ${converted.length} images.`);
  return converted;
}

convertToWebP().catch(console.error);

