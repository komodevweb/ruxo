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
                                   <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">AI Image & Video</Link>
                                   <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">AI Voiceover</Link>
                                   <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Royalty-Free Music</Link>
                                   <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Sound Effects</Link>
                                   <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Stock Footage</Link>
                                   <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Video Templates</Link>
                              </div>

                              {/* Company & Business */}
                              <div className="flex flex-col gap-8">
                                   <div className="flex flex-col gap-4">
                                        <h6 className="text-sm font-medium text-white">Company</h6>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">About Us</Link>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Ruxo for Business</Link>
                                   </div>
                                   <div className="flex flex-col gap-4">
                                        <h6 className="text-sm font-medium text-white">Business Solutions</h6>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Businesses</Link>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Creative Agencies</Link>
                                   </div>
                              </div>

                              {/* Join Us & Help */}
                              <div className="flex flex-col gap-8">
                                   <div className="flex flex-col gap-4">
                                        <h6 className="text-sm font-medium text-white">Join Us</h6>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Become a Creator</Link>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Affiliate Program</Link>
                                   </div>
                                   <div className="flex flex-col gap-4">
                                        <h6 className="text-sm font-medium text-white">Help</h6>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Help Center</Link>
                                   </div>
                              </div>

                              {/* Resources & Legal */}
                              <div className="flex flex-col gap-8">
                                   <div className="flex flex-col gap-4">
                                        <h6 className="text-sm font-medium text-white">Resources</h6>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Ruxo Blog</Link>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">Community</Link>
                                   </div>
                                   <div className="flex flex-col gap-4">
                                        <h6 className="text-sm font-medium text-white">License & Terms</h6>
                                        <Link href="/terms" className="text-sm text-white/60 hover:text-white transition-colors">Terms of Use</Link>
                                        <Link href="/privacy" className="text-sm text-white/60 hover:text-white transition-colors">Privacy Policy</Link>
                                        <Link href="/" className="text-sm text-white/60 hover:text-white transition-colors">License Agreement</Link>
                                   </div>
                              </div>
                         </div>
                    </div>

                    {/* Bottom Section */}
                    <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6">
                         <div className="flex items-center gap-6">
                              <Link href="/" className="text-white/60 hover:text-white transition-colors">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M19.812 5.418c.861.23 1.538.907 1.768 1.768C21.998 8.746 22 12 22 12s0 3.255-.418 4.814a2.504 2.504 0 0 1-1.768 1.768c-1.56.419-7.814.419-7.814.419s-6.255 0-7.814-.419a2.505 2.505 0 0 1-1.768-1.768C2 15.255 2 12 2 12s0-3.255.417-4.814a2.507 2.507 0 0 1 1.768-1.768C5.744 5 11.998 5 11.998 5s6.255 0 7.814.418ZM15.194 12 10 15V9l5.194 3Z" clipRule="evenodd" /></svg>
                              </Link>
                              <Link href="/" className="text-white/60 hover:text-white transition-colors">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M12.315 2c2.43 0 2.784.013 3.808.06 1.064.049 1.791.218 2.427.465a4.902 4.902 0 0 1 1.772 1.153 4.902 4.902 0 0 1 1.153 1.772c.247.636.416 1.363.465 2.427.048 1.067.06 1.407.06 4.123v.08c0 2.643-.012 2.987-.06 4.043-.049 1.064-.218 1.791-.465 2.427a4.902 4.902 0 0 1-1.153 1.772 4.902 4.902 0 0 1-1.772 1.153c-.636.247-1.363.416-2.427.465-1.067.048-1.407.06-4.123.06h-.08c-2.643 0-2.987-.012-4.043-.06-1.064-.049-1.791-.218-2.427-.465a4.902 4.902 0 0 1-1.772-1.153 4.902 4.902 0 0 1-1.153-1.772c-.247-.636-.416-1.363-.465-2.427-.047-1.024-.06-1.379-.06-3.808v-.63c0-2.43.013-2.784.06-3.808.049-1.064.218-1.791.465-2.427a4.902 4.902 0 0 1 1.153-1.772A4.902 4.902 0 0 1 5.468 4.53c.636-.247 1.363-.416 2.427-.465C8.901 2.013 9.256 2 11.685 2h.63Zm-.081 1.802h-.468c-2.456 0-2.784.011-3.807.058-.975.045-1.504.207-1.857.344-.467.182-.8.398-1.15.748-.35.35-.566.683-.748 1.15-.137.353-.3.882-.344 1.857-.047 1.023-.058 1.351-.058 3.807v.468c0 2.456.011 2.784.058 3.807.045.975.207 1.504.344 1.857.182.466.399.8.748 1.15.35.35.683.566 1.15.748.353.137.882.3 1.857.344 1.054.048 1.37.058 4.041.058h.08c2.597 0 2.917-.01 3.96-.058.976-.045 1.505-.207 1.858-.344.466-.182.8-.398 1.15-.748.35-.35.566-.683.748-1.15.137-.353.3-.882.344-1.857.048-1.055.058-1.37.058-4.041v-.08c0-2.597-.01-2.917-.058-3.96-.045-.976-.207-1.505-.344-1.858a3.097 3.097 0 0 0-.748-1.15 3.098 3.098 0 0 0-1.15-.748c-.353-.137-.882-.3-1.857-.344-1.023-.047-1.351-.058-3.807-.058ZM12 6.865a5.135 5.135 0 1 1 0 10.27 5.135 5.135 0 0 1 0-10.27Zm0 1.802a3.333 3.333 0 1 0 0 6.666 3.333 3.333 0 0 0 0-6.666Zm5.338-3.205a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" clipRule="evenodd" /></svg>
                              </Link>
                              <Link href="/" className="text-white/60 hover:text-white transition-colors">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path d="M13.6823 10.6218L20.2391 3H18.6854L12.9921 9.61788L8.44486 3H3.2002L10.0765 13.0074L3.2002 21H4.75404L10.7663 14.0113L15.5685 21H20.8131L13.6819 10.6218H13.6823ZM11.5541 13.0956L10.8574 12.0991L5.31391 4.16971H7.70053L12.1742 10.5689L12.8709 11.5655L18.6861 19.8835H16.2995L11.5541 13.096V13.0956Z"/></svg>
                              </Link>
                              <Link href="/" className="text-white/60 hover:text-white transition-colors">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12Z" clipRule="evenodd" /></svg>
                              </Link>
                              <Link href="/" className="text-white/60 hover:text-white transition-colors">
                                   <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path fillRule="evenodd" d="M12.545,12.151L12.545,12.151c0,1.054,0.855,1.909,1.909,1.909h3.536c-0.607-1.726-1.451-3.468-2.525-5.123c-0.891,1.194-1.438,2.66-1.438,4.241c0,0.545,0.066,1.074,0.19,1.581l-1.672-0.631C12.513,13.649,12.545,12.909,12.545,12.151z M8,16c0-4.418,3.582-8,8-8c0.606,0,1.195,0.068,1.761,0.196C16.122,5.157,13.154,3,9.758,3C4.917,3,1,6.917,1,11.758c0,2.213,0.826,4.236,2.195,5.782C3.08,17.112,3,16.568,3,16c0-2.761,2.239-5,5-5c0.752,0,1.465,0.165,2.111,0.461l0.564-1.409C10.183,10.019,9.603,10,9,10c-3.314,0-6,2.686-6,6c0,0.692,0.119,1.353,0.333,1.973C4.599,20.069,6.996,21.25,9.758,21.25c4.841,0,8.758-3.917,8.758-8.758c0-0.663-0.074-1.309-0.212-1.931C17.807,11.611,17.308,12.61,16.69,13.508C16.9,14.294,17,15.132,17,16c0,0.568-0.08,1.112-0.219,1.636C16.236,17.821,15.654,18,15,18c-3.314,0-6-2.686-6-6c0-0.758,0.155-1.473,0.431-2.128L7.926,10.591C7.336,11.584,7,12.745,7,14c0,4.418,3.582,8,8,8c0.663,0,1.299-0.089,1.906-0.251c-0.431-0.657-0.973-1.23-1.605-1.697C14.678,20.694,13.864,21,13,21C8.582,21,5,17.418,5,13c0-1.678,0.521-3.244,1.41-4.542C7.09,7.528,8.391,6.837,9.847,6.532C10.528,6.191,11.241,6,12,6c3.314,0,6,2.686,6,6c0,1.445-0.516,2.774-1.376,3.825C16.968,15.959,17,15.984,17,16c0,2.761-2.239,5-5,5c-0.321,0-0.633-0.033-0.938-0.094c0.395-0.354,0.737-0.771,1.009-1.234C12.596,19.933,13.28,20,14,20c2.209,0,4-1.791,4-4c0-0.214-0.025-0.423-0.068-0.626C17.969,15.321,18,15.164,18,15c0-1.657-1.343-3-3-3c-0.457,0-0.885,0.109-1.27,0.297C13.373,12.112,13.03,12,12.682,12c-0.349,0-0.692,0.025-1.029,0.072C11.299,12.025,11,12.025,11,12c-2.761,0-5-2.239-5-5c0-0.555,0.095-1.089,0.264-1.592C5.269,6.439,4.548,7.656,4.162,9.048C3.75,10.539,3.553,12.261,3.553,12.261s0.654-1.423,1.868-2.235C6.635,9.215,8.263,9,8.263,9s-1.132,1.062-1.629,2.583c-0.306,0.938-0.329,1.962-0.029,2.911c0.3,0.948,0.985,1.694,1.84,2.091C9.301,16.981,10.138,17,11,17c3.314,0,6-2.686,6-6c0-0.527-0.078-1.035-0.222-1.518C16.928,9.178,17,9.092,17,9C17,5.686,14.314,3,11,3c-0.685,0-1.34,0.116-1.954,0.329C9.819,2.495,10.685,2,11.636,2C16.055,2,19.636,5.582,19.636,10c0,0.404-0.03,0.799-0.088,1.186C20.272,10.869,20.91,10.488,21.477,10.043z" clipRule="evenodd" /></svg>
                              </Link>
                         </div>
                         
                         <div className="flex items-center gap-6">
                              <p className="text-xs font-normal text-white/40">
                                   © {currentYear} Ruxo Inc.
                              </p>
                              <Link href="/" className="text-xs font-normal text-white/60 hover:text-white transition-colors">
                                   Accessibility
                              </Link>
                         </div>
                    </div>
               </div>
          </footer>
     )
}

export default Footer
