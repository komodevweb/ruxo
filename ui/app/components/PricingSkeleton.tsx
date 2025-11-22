"use client";

import { Skeleton } from '@/app/components/SettingsSkeleton';

export function PricingSkeleton() {
  return (
    <div className="grid mb-4 lg:grid-cols-4 md:grid-cols-2 gap-6 mt-6">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="w-full p-[1] rounded-4xl pricing-card-bg"
        >
          <div className="w-full rounded-4xl p-8">
            <Skeleton height="h-6" width="w-24" className="mb-6" />
            
            <div className="flex items-end gap-0.5 mb-3">
              <Skeleton height="h-12" width="w-24" />
              <Skeleton height="h-4" width="w-16" />
            </div>
            
            <Skeleton height="h-4" width="w-32" className="mb-8" />
            
            <Skeleton height="h-10" width="w-full" className="rounded-xl mb-8" />
            
            <Skeleton height="h-5" width="w-40" className="mb-6" />
            
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((j) => (
                <div key={j} className="flex items-center gap-3">
                  <Skeleton height="h-4" width="w-4" className="rounded" />
                  <Skeleton height="h-4" width="w-32" />
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

