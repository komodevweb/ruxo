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
      // Use a 4-hour cycle that loops continuously
      const now = new Date();
      const CYCLE_DURATION = 4 * 60 * 60 * 1000; // 4 hours in milliseconds
      
      // Calculate position within the current 4-hour cycle
      // Using epoch time modulo to create a consistent loop
      const timeInCycle = now.getTime() % CYCLE_DURATION;
      const timeRemaining = CYCLE_DURATION - timeInCycle;
      
      // Convert to hours, minutes, seconds (no days since max is 4 hours)
      const totalSeconds = Math.floor(timeRemaining / 1000);
      
      return {
        days: 0, // Always 0 since max is 4 hours
        hours: Math.floor(totalSeconds / (60 * 60)),
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
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>Free Trial Offer Ends in:</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> hours</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> minutes</h6>
        <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'><span className='mr-0.5 md:mr-1 inline-block'>--</span> seconds</h6>
      </div>
    );
  }

  return (
    <div className='bg-blue2 fixed top-0 left-0 w-full z-[1001] flex-wrap text-center py-1.5 md:py-2 flex gap-2 md:gap-[18px] items-center justify-center px-2'>
      <h6 className='text-[10px] md:text-xs font-medium leading-tight text-black'>Free Trial Offer Ends in:</h6>
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

