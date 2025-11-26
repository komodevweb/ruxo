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
                              <p className="text-base text-white/60">Effective Date: November 26, 2025</p>
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
                                        <strong>Your Content:</strong> You retain ownership of the inputs (text, images, video) you upload to the Platform. However, you represent and warrant that:
                                   </p>
                                   <ul className="list-disc pl-5 mt-2 mb-3 space-y-2 leading-relaxed marker:text-white/60">
                                        <li>You own or have obtained all necessary rights, licenses, and permissions to use and upload the content.</li>
                                        <li>You have obtained explicit written consent from any individuals whose image, video, voice, or likeness appears in your content.</li>
                                        <li>Your content does not infringe upon the intellectual property, privacy, or publicity rights of any third party.</li>
                                        <li>Your content complies with all applicable laws and these Terms of Use.</li>
                                   </ul>
                                   <p className="leading-relaxed mb-2">
                                        <strong>Generated Assets:</strong> Subject to your compliance with these Terms, Ruxo assigns to you all right, title, and interest in and to the assets you generate using the Platform. You are free to use these assets for personal or commercial purposes, provided that:
                                   </p>
                                   <ul className="list-disc pl-5 mt-2 space-y-2 leading-relaxed marker:text-white/60">
                                        <li>The generated content does not violate any laws or these Terms of Use.</li>
                                        <li>You do not use generated content to impersonate others or create misleading or harmful content.</li>
                                        <li>You respect the rights of any individuals depicted in or affected by the generated content.</li>
                                   </ul>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">5. Acceptable Use & Prohibited Content</h2>
                                   <p className="leading-relaxed mb-3">
                                        You agree not to use the Platform to generate content that is illegal, harmful, threatening, abusive, harassing, defamatory, or otherwise objectionable. We reserve the right to suspend or terminate accounts that violate this policy.
                                   </p>
                                   <p className="leading-relaxed mb-3">
                                        <strong>Strictly Prohibited Content:</strong> The following types of content are strictly prohibited and will result in immediate account suspension or termination:
                                   </p>
                                   <ul className="list-disc pl-5 mt-2 space-y-2 leading-relaxed marker:text-white/60">
                                        <li><strong>Impersonation:</strong> You may not use the Platform to create content that impersonates or misrepresents another person, including but not limited to creating deepfakes, voice clones, or any content that falsely represents someone's identity, appearance, or voice without their explicit written consent.</li>
                                        <li><strong>Pornography & Nudity:</strong> You may not generate, upload, or request any content that contains explicit sexual material, pornography, or nudity. This includes but is not limited to sexual acts, explicit sexual content, or graphic nudity.</li>
                                        <li><strong>Unauthorized Use of Others' Content:</strong> You may not upload, use, or generate content using someone else's image, video, voice, or likeness without their explicit written permission. This includes using videos, photos, or audio recordings of individuals without their consent.</li>
                                        <li><strong>Harmful or Dangerous Content:</strong> Content that promotes violence, self-harm, terrorism, or illegal activities is strictly prohibited.</li>
                                        <li><strong>Harassment & Bullying:</strong> Content designed to harass, bully, threaten, or intimidate individuals or groups is not allowed.</li>
                                        <li><strong>Copyright Infringement:</strong> You may not use copyrighted material (including images, videos, music, or text) without proper authorization or licensing.</li>
                                        <li><strong>Misinformation:</strong> Creating or spreading false information, including fake news, doctored evidence, or misleading content, is prohibited.</li>
                                        <li><strong>Minors:</strong> Any content involving or depicting minors in inappropriate, sexual, or harmful contexts is strictly prohibited and will be reported to appropriate authorities.</li>
                                   </ul>
                                   <p className="leading-relaxed mt-4">
                                        <strong>Content Moderation:</strong> We employ automated and manual content moderation systems to detect and remove prohibited content. We reserve the right to review, reject, remove, or report any content that violates these terms. Violations may result in immediate account suspension or termination, and in severe cases, we may report illegal content to law enforcement authorities.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">6. Safety & Security Measures</h2>
                                   <p className="leading-relaxed mb-3">
                                        Ruxo is committed to maintaining a safe platform. We implement multiple layers of protection:
                                   </p>
                                   <ul className="list-disc pl-5 mt-2 space-y-2 leading-relaxed marker:text-white/60">
                                        <li><strong>Content Filtering:</strong> Advanced AI and human moderation systems screen all content for prohibited material.</li>
                                        <li><strong>Real-time Monitoring:</strong> We continuously monitor platform activity to detect and prevent abuse.</li>
                                        <li><strong>User Reporting:</strong> Users can report violations, and we investigate all reports promptly.</li>
                                        <li><strong>Account Verification:</strong> We may require identity verification for certain features or when suspicious activity is detected.</li>
                                        <li><strong>Rate Limiting:</strong> We implement rate limits to prevent abuse and ensure fair usage.</li>
                                        <li><strong>Legal Compliance:</strong> We cooperate with law enforcement and comply with all applicable laws regarding harmful content.</li>
                                   </ul>
                                   <p className="leading-relaxed mt-4">
                                        By using Ruxo, you agree to cooperate with our safety measures and understand that we may take action, including account suspension or termination, to protect our community.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">7. Subscription & Pricing</h2>
                                   <p className="leading-relaxed">
                                        Certain features require a paid subscription (Pro or Ultimate). Pricing and terms for these subscriptions are available on our Pricing page. All fees are non-refundable except as required by law.
                                   </p>
                              </section>

                              <section>
                                   <h2 className="text-xl font-medium text-white mb-3">8. Limitation of Liability</h2>
                                   <p className="leading-relaxed">
                                        Ruxo is provided "as is" without warranties of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the Platform. You are solely responsible for ensuring that your use of generated content complies with all applicable laws and that you have obtained all necessary permissions and consents.
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

