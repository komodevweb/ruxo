"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import { useAuth } from "@/contexts/AuthContext";

function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut, loading } = useAuth();

  const authPages = ["/login-email", "/signup-email", "/forgot-password", "/login", "/signup-password", "/signup", "/verify-email"];

  const isAuthPage = authPages.includes(pathname);

  const handleSignOut = async () => {
    await signOut();
    router.push("/");
  };

  if (isAuthPage) {
    return null;
  }

  return (
    <header className="bg-black-1100/80 backdrop-blur-md fixed left-0 w-full top-[24px] md:top-[32px] z-[1000] p-4 font-inter flex items-center justify-between">
      <Link href="/">
        <img src="/images/logo.svg" className="h-[28.8px] md:h-[38.4px] md:w-auto w-auto" alt="Ruxo" />
      </Link>

      <div className="flex items-center">
        {loading ? (
          <div className="relative overflow-hidden bg-gray-1200/30 rounded-lg">
            <div className="md:text-sm text-xs font-medium text-gray-1100 py-[9.5px] px-3.5">
              <div className="h-4 w-20 bg-gray-1200/50 rounded relative overflow-hidden">
                <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              </div>
            </div>
          </div>
        ) : !user ? (
          <div className="flex items-center md:gap-4 gap-2">
            <Link href="/login" className="md:text-sm text-xs font-medium transition-all hover:text-white text-gray-1100 inline-block py-[9.5px] px-3.5 border border-gray-1200 rounded-xl">
              Log In
            </Link>

            <Link href="/signup" className="md:text-sm text-xs font-bold transition-all duration-300 shadow-3xl hover:shadow-7xl text-black inline-block py-[9.5px] px-3.5 bg1 rounded-xl">
              Get Started
            </Link>
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <Link 
              href="/upgrade" 
              className="text-xs font-bold transition-all duration-300 shadow-3xl hover:shadow-7xl text-black inline-block py-2 px-3 bg1 rounded-lg"
            >
              Get More Credits
            </Link>
            <Menu>
              <MenuButton className="inline-flex cursor-pointer focus:outline-none items-center gap-2 md:text-sm text-xs font-medium text-white/60 bg-transparent">
                <img 
                  src={user.avatar_url || "/images/avatar.svg"} 
                  alt={user.display_name || "User"} 
                  className="w-8 h-8 rounded-full object-cover"
                />
                <span className="hidden md:inline">Account</span>
              </MenuButton>

              <MenuItems
                transition
                anchor="bottom end"
                className="w-[237px] mt-2! dropdown-bg origin-top-right z-[999] rounded-lg p-5 text-white transition duration-200 ease-out data-[closed]:scale-95 data-[closed]:opacity-0 focus:outline-none shadow-4xl backdrop-blur-[21.5px]"
              >
                <div className='flex items-center gap-3 mb-4 pb-4 border-b border-white/10'>
                  <img 
                    src={user.avatar_url || "/images/avatar.svg"} 
                    alt={user.display_name || "User"} 
                    className="w-10 h-10 rounded-full object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <p className='text-sm font-medium text-white truncate'>{user.display_name || "User"}</p>
                    <p className='text-xs text-white/60 truncate'>{user.email}</p>
                  </div>
                </div>
                <div className='flex items-center justify-between mb-2'>
                  <h6 className='text-sm font-normal text-white/60 relative overflow-hidden rounded'>
                    <span className="relative z-10">Credit Usage</span>
                    <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/5 to-transparent" />
                  </h6>
                  <h6 className='text-sm font-normal text-white/60 relative overflow-hidden rounded'>
                    <span className="relative z-10">
                      {user ? (
                        user.credits_per_month 
                          ? `${user.credit_balance || 0}/${user.credits_per_month}`
                          : `${user.credit_balance || 0}`
                      ) : "0"}
                    </span>
                    <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/5 to-transparent" />
                  </h6>
                </div>
                <div className='h-1.5 mb-5 rounded-[17px] mt-2 overflow-hidden bg-gray-1200/[50%] relative'>
                  <div 
                    className='rounded-[17px] h-1.5 progress-bg relative overflow-hidden'
                    style={{ 
                      width: user && user.credits_per_month 
                        ? `${Math.min(((user.credit_balance || 0) / user.credits_per_month) * 100, 100)}%` 
                        : user && user.credit_balance 
                          ? "100%" 
                          : "0%" 
                    }}
                  >
                    <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                  </div>
                </div>

                <Link href="/settings" className='text-base cursor-pointer mb-5 text-white/60 flex items-center gap-2 bg-transparent hover:text-white transition-colors'>
                  <img src="/images/settings-icon.svg" alt="" />
                  Manage Account
                </Link>

                <button
                  onClick={handleSignOut}
                  className='text-base cursor-pointer text-white/60 flex items-center gap-2 bg-transparent hover:text-white transition-colors w-full text-left'
                >
                  <img src="/images/SignOut.svg" alt="" />
                  Log Out
                </button>
              </MenuItems>
            </Menu>
          </div>
        )}
      </div>
    </header>
  );
}

export default Header;
