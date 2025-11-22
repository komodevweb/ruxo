"use client";

interface SkeletonProps {
  className?: string;
  height?: string;
  width?: string;
}

export function Skeleton({ className = "", height = "h-4", width = "w-full" }: SkeletonProps) {
  return (
    <div
      className={`${height} ${width} bg-gray-1200/30 rounded-lg relative overflow-hidden ${className}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  );
}

export function SettingsSkeleton() {
  return (
    <div className="font-inter">
      <section className="py-12 md:pt-[160px] pt-[110px] min-h-[calc(100vh_-_56px)] bg-black-1100 flex items-center justify-center">
        <div className='max-w-[740px] w-full px-5 mx-auto'>
          {/* Profile Header Skeleton */}
          <div className='icon-bg p-6 mb-6 shadow-4xl rounded-2xl flex items-center gap-6'>
            <Skeleton height="h-16" width="w-16" className="rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton height="h-6" width="w-48" />
              <Skeleton height="h-4" width="w-64" />
            </div>
          </div>

          {/* Plan Details Skeleton */}
          <div className='icon-bg p-6 mb-6 shadow-4xl space-y-6 rounded-2xl'>
            <Skeleton height="h-5" width="w-32" />
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Skeleton height="h-4" width="w-32" />
                <Skeleton height="h-4" width="w-16" />
              </div>
              <Skeleton height="h-1.5" width="w-full" className="rounded-[17px]" />
              <div className="flex items-center justify-between mt-8">
                <Skeleton height="h-4" width="w-28" />
                <Skeleton height="h-3" width="w-20" />
              </div>
              <Skeleton height="h-5" width="w-24" />
            </div>
          </div>

          {/* Account Details Skeleton */}
          <div className='icon-bg p-6 mb-6 shadow-4xl space-y-6 rounded-2xl'>
            <Skeleton height="h-5" width="w-40" />
            <div className='space-y-8'>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Skeleton height="h-4" width="w-32" />
                  <Skeleton height="h-3" width="w-12" />
                </div>
                <Skeleton height="h-5" width="w-48" />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Skeleton height="h-4" width="w-20" />
                  <Skeleton height="h-3" width="w-12" />
                </div>
                <Skeleton height="h-5" width="w-64" />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Skeleton height="h-4" width="w-24" />
                  <Skeleton height="h-3" width="w-12" />
                </div>
                <Skeleton height="h-5" width="w-48" />
              </div>
            </div>
          </div>

          {/* Actions Skeleton */}
          <div className='icon-bg p-6 shadow-4xl flex items-center justify-between rounded-2xl'>
            <Skeleton height="h-5" width="w-24" />
            <Skeleton height="h-4" width="w-32" />
          </div>
        </div>
      </section>
    </div>
  );
}

