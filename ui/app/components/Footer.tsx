import Link from 'next/link'
import React from 'react'

interface FooterProps {
     className?: string
}

function Footer({ className }: FooterProps) {
     const currentYear = new Date().getFullYear();

     return (
          <footer className={`${className || 'bg-black-1100'} w-full border-t border-white/5 pt-16 pb-8 font-inter`}>
               <div className="max-w-[1320px] mx-auto px-5">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-16">
                         {/* Brand Column */}
                         <div className="lg:col-span-4">
                              <Link href="/" className="inline-block mb-6">
                                   <img src="/images/logo.svg" alt="Ruxo" className="h-[38.4px] w-auto" />
                              </Link>
                              <h5 className="text-base font-medium text-white mb-4">About us</h5>
                              <p className="text-sm text-white/60 leading-relaxed max-w-[360px]">
                                   Our mission is to empower creators and brands to bring their vision to life with video. We provide the newest AI tools and models for image, video, and voiceover, all in one place.
                              </p>
                         </div>

                         {/* Links Columns */}
                         <div className="lg:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-8">
                              {/* Products */}
                              <div className="flex flex-col gap-4">
                                   <h6 className="text-sm font-medium text-white">Products</h6>
                                   <Link href="/image" className="text-sm text-white/60 hover:text-white transition-colors">Text to Image</Link>
                                   <Link href="/image-to-video" className="text-sm text-white/60 hover:text-white transition-colors">Image to Video</Link>
                                   <Link href="/text-to-video" className="text-sm text-white/60 hover:text-white transition-colors">Text to Video</Link>
                                   <Link href="/wan-animate" className="text-sm text-white/60 hover:text-white transition-colors">Wan Animate</Link>
                              </div>

                              {/* Pages */}
                              <div className="flex flex-col gap-4">
                                   <h6 className="text-sm font-medium text-white">Pages</h6>
                                   <Link href="/pricing" className="text-sm text-white/60 hover:text-white transition-colors">Pricing</Link>
                                   <Link href="/terms" className="text-sm text-white/60 hover:text-white transition-colors">Terms of Use</Link>
                                   <Link href="/privacy" className="text-sm text-white/60 hover:text-white transition-colors">Privacy Policy</Link>
                              </div>
                         </div>
                    </div>

                    {/* Bottom Section */}
                    <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6">
                         <div className="flex items-center gap-6">
                              <Link href="https://youtube.com/@ruxo" target="_blank" rel="noopener noreferrer" className="text-white/60 hover:text-white transition-colors" aria-label="YouTube">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M19.812 5.418c.861.23 1.538.907 1.768 1.768C21.998 8.746 22 12 22 12s0 3.255-.418 4.814a2.504 2.504 0 0 1-1.768 1.768c-1.56.419-7.814.419-7.814.419s-6.255 0-7.814-.419a2.505 2.505 0 0 1-1.768-1.768C2 15.255 2 12 2 12s0-3.255.417-4.814a2.507 2.507 0 0 1 1.768-1.768C5.744 5 11.998 5 11.998 5s6.255 0 7.814.418ZM15.194 12 10 15V9l5.194 3Z" clipRule="evenodd" /></svg>
                              </Link>
                              <Link href="https://instagram.com/ruxo" target="_blank" rel="noopener noreferrer" className="text-white/60 hover:text-white transition-colors" aria-label="Instagram">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M12.315 2c2.43 0 2.784.013 3.808.06 1.064.049 1.791.218 2.427.465a4.902 4.902 0 0 1 1.772 1.153 4.902 4.902 0 0 1 1.153 1.772c.247.636.416 1.363.465 2.427.048 1.067.06 1.407.06 4.123v.08c0 2.643-.012 2.987-.06 4.043-.049 1.064-.218 1.791-.465 2.427a4.902 4.902 0 0 1-1.153 1.772 4.902 4.902 0 0 1-1.772 1.153c-.636.247-1.363.416-2.427.465-1.067.048-1.407.06-4.123.06h-.08c-2.643 0-2.987-.012-4.043-.06-1.064-.049-1.791-.218-2.427-.465a4.902 4.902 0 0 1-1.772-1.153 4.902 4.902 0 0 1-1.153-1.772c-.247-.636-.416-1.363-.465-2.427-.047-1.024-.06-1.379-.06-3.808v-.63c0-2.43.013-2.784.06-3.808.049-1.064.218-1.791.465-2.427a4.902 4.902 0 0 1 1.153-1.772A4.902 4.902 0 0 1 5.468 4.53c.636-.247 1.363-.416 2.427-.465C8.901 2.013 9.256 2 11.685 2h.63Zm-.081 1.802h-.468c-2.456 0-2.784.011-3.807.058-.975.045-1.504.207-1.857.344-.467.182-.8.398-1.15.748-.35.35-.566.683-.748 1.15-.137.353-.3.882-.344 1.857-.047 1.023-.058 1.351-.058 3.807v.468c0 2.456.011 2.784.058 3.807.045.975.207 1.504.344 1.857.182.466.399.8.748 1.15.35.35.683.566 1.15.748.353.137.882.3 1.857.344 1.054.048 1.37.058 4.041.058h.08c2.597 0 2.917-.01 3.96-.058.976-.045 1.505-.207 1.858-.344.466-.182.8-.398 1.15-.748.35-.35.566-.683.748-1.15.137-.353.3-.882.344-1.857.048-1.055.058-1.37.058-4.041v-.08c0-2.597-.01-2.917-.058-3.96-.045-.976-.207-1.505-.344-1.858a3.097 3.097 0 0 0-.748-1.15 3.098 3.098 0 0 0-1.15-.748c-.353-.137-.882-.3-1.857-.344-1.023-.047-1.351-.058-3.807-.058ZM12 6.865a5.135 5.135 0 1 1 0 10.27 5.135 5.135 0 0 1 0-10.27Zm0 1.802a3.333 3.333 0 1 0 0 6.666 3.333 3.333 0 0 0 0-6.666Zm5.338-3.205a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" clipRule="evenodd" /></svg>
                              </Link>
                              <Link href="https://facebook.com/ruxo" target="_blank" rel="noopener noreferrer" className="text-white/60 hover:text-white transition-colors" aria-label="Facebook">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12Z" clipRule="evenodd" /></svg>
                              </Link>
                         </div>
                         
                         <div className="flex items-center gap-6">
                              <p className="text-xs font-normal text-white/40">
                                   © {currentYear} Ruxo Inc.
                              </p>
                         </div>
                    </div>
               </div>
          </footer>
     )
}

export default Footer
