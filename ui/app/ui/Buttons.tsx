import Link from "next/link";

interface SocialButtonProps {
     href: string;
     icon: string;
     text: string;
     className?: string;
}

export default function Buttons({
     href,
     icon,
     text,
     className = "",
}: SocialButtonProps) {
     return (
          <Link
               href={href}
               className={`text-base font-medium leading-[120%] transition-all ease-in-out duration-500 hover:bg-gray-1800 text-black-1000 bg-white rounded-xl border border-gray-1100 flex items-center py-2.5 justify-center gap-2 ${className}`}
          >
               <img src={icon} alt={text} />
               {text}
          </Link>
     );
}
