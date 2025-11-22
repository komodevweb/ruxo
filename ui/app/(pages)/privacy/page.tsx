import Footer from "@/app/components/Footer"
import Link from "next/link"

function page() {
     return (
          <div className="font-inter bg-black-1100">
               <section className="md:py-[88px] py-20 md:pt-[160px] pt-[110px] min-h-[calc(100vh_-_56px)]">
                    <div className="max-w-[900px] w-full px-5 mx-auto">
                         <div className="text-center mb-12">
                              <h1 className="md:text-[48px] text-[32px] text-white font-medium leading-[120%] tracking-[-1px] mb-4">Privacy Policy</h1>
                              <p className="text-base text-white/60">Effective Date: November 20, 2025</p>
                         </div>

                         <div className="space-y-8 text-white/80">
                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">1. Introduction</h2>
                                   <p className="leading-relaxed">
                                        Ruxo ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our AI creation platform.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">2. Information We Collect</h2>
                                   <ul className="list-disc pl-5 space-y-2 leading-relaxed marker:text-white/60">
                                        <li><strong>Account Information:</strong> Email address, username, and password when you register.</li>
                                        <li><strong>User Content:</strong> Images, videos, and text prompts you upload or input into the Platform.</li>
                                        <li><strong>Usage Data:</strong> Information about how you interact with our services, including generation history and preferences.</li>
                                   </ul>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">3. How We Use Your Information</h2>
                                   <p className="leading-relaxed">
                                        We use your information to:
                                   </p>
                                   <ul className="list-disc pl-5 mt-2 space-y-2 leading-relaxed marker:text-white/60">
                                        <li>Provide, maintain, and improve our AI services.</li>
                                        <li>Process your generations using AI models (e.g., Wan 2.2).</li>
                                        <li>Communicate with you about your account and updates.</li>
                                        <li>Ensure the security of our Platform.</li>
                                   </ul>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">4. AI Processing & Data Retention</h2>
                                   <p className="leading-relaxed">
                                        Your uploads and prompts are processed by our AI models to generate content. We may temporarily store this data to fulfill your requests. We do not use your private content to train our public models without your explicit consent.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">5. Data Sharing</h2>
                                   <p className="leading-relaxed">
                                        We do not sell your personal data. We may share information with trusted third-party service providers who assist us in operating our Platform (e.g., cloud hosting, payment processing), subject to confidentiality obligations.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">6. Your Rights</h2>
                                   <p className="leading-relaxed">
                                        You have the right to access, correct, or delete your personal information. You can manage your account settings directly on the Platform or contact us for assistance.
                                   </p>
                              </section>

                              <div className="pt-8 border-t border-white/10 mt-12">
                                   <p className="text-sm text-white/60">
                                        If you have any questions about this Privacy Policy, please contact us at privacy@ruxo.com.
                                   </p>
                              </div>
                         </div>
                    </div>
               </section>
               <Footer />
          </div>
     )
}

export default page

