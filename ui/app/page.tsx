
import Footer from "./components/Footer";
import FeaturedModels from "./components/FeaturedModels";
import ImageGallery from "./components/ImageGallery";
import HomepageCards from "./components/HomepageCards";


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
            <span className="text-[10px] font-medium leading-2.5 text-black py-1 px-[11px] inline-block bg-blue-1000 rounded-full">AI Creation Platform</span>
            <h1 className="md:text-[68px] text-[38px] text-white font-medium md:mt-5 mt-4 mb-4 leading-[120%] tracking-[-1px]">Create Anything You Imagine</h1>
            <p className="md:text-base text-sm font-medium leading-[120%] text-white/60">Turn your ideas into amazing videos, images, and visuals. Just type what you want and watch the magic happen.</p>
          </div>
          <div className="md:mt-20 mt-12">
            <HomepageCards />
          </div>
          <FeaturedModels />
        </div>
      </section>
      <ImageGallery />
      <Footer></Footer>
    </div>
  );
}
