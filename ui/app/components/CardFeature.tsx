import Link from "next/link";

interface CardFeatureProps {
     image: string;
     icon: string;
     title: string;
     description: string;
     link: string;
}

export default function CardFeature({
     image,
     icon,
     title,
     description,
     link,
}: CardFeatureProps) {
     return (
          <Link href={link} className="block">
               <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500 cursor-pointer">
                    <div className="w-full overflow-hidden rounded-xl">
                         <img 
                              src={image} 
                              alt={title} 
                              className="w-full h-auto object-cover"
                              loading="lazy"
                              decoding="async"
                         />
                    </div>

                    <div className="mt-2 py-4 px-2 flex items-start gap-4">
                         <div className="w-12 h-12 rounded-xl flex items-center justify-center icon-bg">
                              <img src={icon} alt={`${title} icon`} />
                         </div>

                         <div className="flex-1">
                              <h4 className="text-xl font-medium leading-[120%] text-white">
                                   {title}
                              </h4>

                              <p className="text-base font-normal leading-[120%] text-white/60 mt-2 mb-4">
                                   {description}
                              </p>

                              <div className="flex items-center gap-2 text-white text-sm font-medium leading-4">
                                   Try It Now <img src="/images/arrow-right.svg" alt="" />
                              </div>
                         </div>
                    </div>
               </div>
          </Link>
     );
}
