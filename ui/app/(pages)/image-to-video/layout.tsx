import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Image to Video AI Generator - Ruxo - Transform Images into Dynamic Videos",
  description: "Transform your images into dynamic videos with lifelike motion and effects. Convert static photos into animated videos using advanced AI technology.",
  keywords: "image to video, AI video generator, photo to video, image animation, video generation from image, AI video converter",
  openGraph: {
    title: "Image to Video AI Generator - Ruxo",
    description: "Transform your images into dynamic videos with lifelike motion and effects using advanced AI.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Image to Video AI Generator - Ruxo",
    description: "Transform your images into dynamic videos with lifelike motion and effects.",
  },
};

export default function ImageToVideoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

