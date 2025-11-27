'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

function Timer() {
  const { user, loading } = useAuth();
  const [timeLeft, setTimeLeft] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0
  });
  const [mounted, setMounted] = useState(false);

  // If user has a plan, don't show timer
  // We check for plan_name existence and that it's not a free plan if your system uses "Free" as a plan name
  const hasPlan = user && user.plan_name && user.plan_name.toLowerCase() !== 'free';

  useEffect(() => {
    setMounted(true);
    
    const calculateTimeLeft = () => {
      // Use user's local time for a synchronized 24-hour loop
      const now = new Date();
      const CYCLE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
      
      // Calculate time since midnight in user's local timezone
      const midnight = new Date(now);
      midnight.setHours(0, 0, 0, 0);
      const timeSinceMidnight = now.getTime() - midnight.getTime();
      
      // Calculate time remaining in current 24-hour cycle
      const timeRemaining = CYCLE_DURATION - timeSinceMidnight;
      
      // Convert to days, hours, minutes, seconds
      const totalSeconds = Math.floor(timeRemaining / 1000);
      
      return {
        days: Math.floor(totalSeconds / (60 * 60 * 24)),
        hours: Math.floor((totalSeconds % (60 * 60 * 24)) / (60 * 60)),
        minutes: Math.floor((totalSeconds % (60 * 60)) / 60),
        seconds: totalSeconds % 60
      };
    };

    // Update immediately
    setTimeLeft(calculateTimeLeft());

    // Update every second
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Hide timer while loading to prevent flash for paid users, or if user has a plan
  if (loading || hasPlan) {
    return null;
  }

  // Prevent hydration mismatch by showing placeholder until mounted
  if (!mounted) {
    return (
      <div className='bg-blue2 fixed top-0 left-0 w-full z-[1001] flex-wrap text-center py-1.5 md:py-2 flex gap-2 md:gap-[18px] items-center justify-center px-2'>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>Limited Time Offer: 70% Off</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> days</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> hours</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> minutes</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> seconds</h6>
      </div>
    );
  }

  return (
    <div className='bg-blue2 fixed top-0 left-0 w-full z-[1001] flex-wrap text-center py-1.5 md:py-2 flex gap-2 md:gap-[18px] items-center justify-center px-2'>
      <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>Limited Time Offer: 70% Off</h6>
      <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>
        <span className='mr-0.5 md:mr-1 inline-block'>{timeLeft.days}</span> days
      </h6>
      <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>
        <span className='mr-0.5 md:mr-1 inline-block'>{timeLeft.hours}</span> hours
      </h6>
      <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>
        <span className='mr-0.5 md:mr-1 inline-block'>{timeLeft.minutes}</span> minutes
      </h6>
      <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>
        <span className='mr-0.5 md:mr-1 inline-block'>{timeLeft.seconds}</span> seconds
      </h6>
    </div>
  );
}

export default Timer;

