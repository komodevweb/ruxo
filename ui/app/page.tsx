import Footer from "./components/Footer";
import FeaturedModels from "./components/FeaturedModels";
import ImageGallery from "./components/ImageGallery";
import HomepageCards from "./components/HomepageCards";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ruxo - Create winning ads with AI",
  description: "Use our library of 100+ captivating AI actors or create your own AI Avatar. Create winning ads with AI.",
  keywords: "AI UGC, AI ads, AI actors, AI avatar, video marketing, AI video generation",
  openGraph: {
    title: "Ruxo - Create winning ads with AI",
    description: "Use our library of 100+ captivating AI actors or create your own AI Avatar.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Ruxo - Create winning ads with AI",
    description: "Use our library of 100+ captivating AI actors or create your own AI Avatar.",
  },
};

export default function Home() {
  return (
    <div className="font-inter bg-black-1100 min-h-screen">
      {/* Background Image Container */}
      <div className="absolute top-0 left-0 w-full h-[800px] md:h-[1000px] bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover pointer-events-none z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black-1100"></div>
      </div>

      {/* Content */}
      <section className="relative z-10 md:py-[88px] md:pt-[160px] pt-[110px] py-12">
        <div className="max-w-[1320px] px-5 mx-auto">
          <div className="text-center">
            <span className="text-[10px] font-medium leading-2.5 text-black py-1 px-[11px] inline-block bg-blue-1000 rounded-full uppercase tracking-wide">AI UGC Maker</span>
            <h1 className="md:text-[68px] text-[38px] text-white font-medium md:mt-5 mt-4 mb-4 leading-[120%] tracking-[-1px]">Create winning ads <span className="italic font-serif font-light">with AI</span></h1>
            <p className="md:text-base text-sm font-medium leading-[120%] text-white/60 mb-8 max-w-xl mx-auto">Use our library of 100+ captivating AI actors or create your own AI Avatar</p>
            <button className="bg-white text-black px-8 py-3 rounded-full font-medium text-sm hover:bg-gray-200 transition-colors">
              Create Free AI Ad
            </button>
          </div>
          <div className="md:mt-20 mt-12">
            <HomepageCards />
          </div>
          <div className="mt-24 mb-12 text-center">
            <p className="text-white/80 text-xl mb-8 font-serif italic">Used by millions of the best marketers</p>
            {/* Placeholder for logos */}
             <div className="flex justify-center gap-8 flex-wrap opacity-50 grayscale">
                {/* Replace with actual logo images/components later */}
                <div className="h-8 w-24 bg-white/20 rounded"></div>
                <div className="h-8 w-24 bg-white/20 rounded"></div>
                <div className="h-8 w-24 bg-white/20 rounded"></div>
                <div className="h-8 w-24 bg-white/20 rounded"></div>
             </div>
          </div>
          <FeaturedModels />
        </div>
      </section>
      <ImageGallery />
      <Footer></Footer>
    </div>
  );
}
