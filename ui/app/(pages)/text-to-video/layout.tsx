import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Text to Video AI Generator - Ruxo - Create Cinematic Videos from Text",
  description: "Turn your text into cinematic video scenes with smart visual storytelling. Generate high-quality videos from text prompts using advanced AI models like Sora 2 Pro and G Veo 3.1.",
  keywords: "text to video, AI video generator, text to video AI, video generation AI, AI video creator, cinematic video AI",
  openGraph: {
    title: "Text to Video AI Generator - Ruxo",
    description: "Turn your text into cinematic video scenes with smart visual storytelling using advanced AI models.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Text to Video AI Generator - Ruxo",
    description: "Turn your text into cinematic video scenes with smart visual storytelling.",
  },
};

export default function TextToVideoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

