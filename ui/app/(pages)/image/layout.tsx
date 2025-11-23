import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Text to Image AI Generator - Ruxo - Create Stunning AI Images",
  description: "Generate original images from text prompts using the latest AI models. Turn your imagination into reality with Ruxo's powerful text-to-image AI generator.",
  keywords: "text to image, AI image generator, AI art generator, image generation AI, text to image AI, AI image creator",
  openGraph: {
    title: "Text to Image AI Generator - Ruxo",
    description: "Generate original images from text prompts using the latest AI models. Turn your imagination into reality.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Text to Image AI Generator - Ruxo",
    description: "Generate original images from text prompts using the latest AI models.",
  },
};

export default function ImageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

