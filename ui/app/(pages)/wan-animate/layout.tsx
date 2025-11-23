import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Wan Animate AI - Ruxo - Turn Any Image into Motion",
  description: "Turn any image into motion with AI-powered animation. Create dynamic animated videos from static images using Wan Animate technology.",
  keywords: "wan animate, image animation, AI animation, photo animation, image to animation, AI motion generator",
  openGraph: {
    title: "Wan Animate AI - Ruxo",
    description: "Turn any image into motion with AI-powered animation. Create dynamic animated videos from static images.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Wan Animate AI - Ruxo",
    description: "Turn any image into motion with AI-powered animation.",
  },
};

export default function WanAnimateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

