import Footer from "@/app/components/Footer"
import Link from "next/link"
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Use - Ruxo - Service Terms & Conditions",
  description: "Read Ruxo's Terms of Use to understand the rules and guidelines for using our AI creation platform and services.",
  keywords: "terms of use, terms and conditions, service terms, Ruxo terms",
  openGraph: {
    title: "Terms of Use - Ruxo",
    description: "Read Ruxo's Terms of Use to understand the rules and guidelines for using our AI creation platform.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Terms of Use - Ruxo",
    description: "Read Ruxo's Terms of Use to understand our service terms and conditions.",
  },
};

function page() {
     return (
          <div className="font-inter bg-black-1100">
               <section className="md:py-[88px] py-20 md:pt-[160px] pt-[110px] min-h-[calc(100vh_-_56px)]">
                    <div className="max-w-[900px] w-full px-5 mx-auto">
                         <div className="text-center mb-12">
                              <h1 className="md:text-[48px] text-[32px] text-white font-medium leading-[120%] tracking-[-1px] mb-4">Terms of Use</h1>
                              <p className="text-base text-white/60">Effective Date: November 20, 2025</p>
                         </div>

                         <div className="space-y-8 text-white/80">
                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">1. Acceptance of Terms</h2>
                                   <p className="leading-relaxed">
                                        By accessing or using Ruxo ("Platform"), you agree to be bound by these Terms of Use. If you do not agree to these terms, please do not use our services.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">2. Description of Service</h2>
                                   <p className="leading-relaxed">
                                        Ruxo is an AI creation platform that allows users to generate text, images, and videos using artificial intelligence models. We provide tools such as Video Re-Animate, Script to Scene, Photo Motion, and more.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">3. User Accounts</h2>
                                   <p className="leading-relaxed">
                                        To access certain features, you may be required to create an account. You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">4. User Content & Intellectual Property</h2>
                                   <p className="leading-relaxed mb-2">
                                        <strong>Your Content:</strong> You retain ownership of the inputs (text, images, video) you upload to the Platform.
                                   </p>
                                   <p className="leading-relaxed">
                                        <strong>Generated Assets:</strong> Subject to your compliance with these Terms, Ruxo assigns to you all right, title, and interest in and to the assets you generate using the Platform. You are free to use these assets for personal or commercial purposes.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">5. Acceptable Use</h2>
                                   <p className="leading-relaxed">
                                        You agree not to use the Platform to generate content that is illegal, harmful, threatening, abusive, harassing, defamatory, or otherwise objectionable. We reserve the right to suspend or terminate accounts that violate this policy.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">6. Subscription & Pricing</h2>
                                   <p className="leading-relaxed">
                                        Certain features require a paid subscription (Pro or Ultimate). Pricing and terms for these subscriptions are available on our Pricing page. All fees are non-refundable except as required by law.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">7. Limitation of Liability</h2>
                                   <p className="leading-relaxed">
                                        Ruxo is provided "as is" without warranties of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the Platform.
                                   </p>
                              </section>

                              <div className="pt-8 border-t border-white/10 mt-12">
                                   <p className="text-sm text-white/60">
                                        Contact us at support@ruxo.com for any questions regarding these Terms.
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

