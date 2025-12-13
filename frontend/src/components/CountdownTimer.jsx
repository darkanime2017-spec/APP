import React, { useState, useEffect } from 'react';

const calculateTimeLeft = (targetDate) => {
  const difference = +new Date(targetDate) - +new Date();
  let timeLeft = {};

  if (difference > 0) {
    timeLeft = {
      days: Math.floor(difference / (1000 * 60 * 60 * 24)),
      hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
      minutes: Math.floor((difference / 1000 / 60) % 60),
      seconds: Math.floor((difference / 1000) % 60),
    };
  }
  return timeLeft;
};

const TimeBlock = ({ value, label }) => (
  <div className="time-block">
    <div className="time-value">{String(value).padStart(2, '0')}</div>
    <div className="time-label">{label}</div>
  </div>
);

function CountdownTimer({ endTime, graceMinutes, onTimeUp }) {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft(endTime));
  const [isGracePeriod, setIsGracePeriod] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      const now = new Date();
      const endDate = new Date(endTime);
      const gracePeriodEndDate = new Date(endDate.getTime() + graceMinutes * 60000);

      if (now > gracePeriodEndDate) {
        setTimeLeft({});
        setIsGracePeriod(false);
      } else if (now > endDate) {
        setTimeLeft(calculateTimeLeft(gracePeriodEndDate));
        setIsGracePeriod(true);
      } else {
        setTimeLeft(calculateTimeLeft(endDate));
        setIsGracePeriod(false);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [timeLeft, endTime, graceMinutes]);

  const hasTimeEnded = Object.keys(timeLeft).length === 0;

  useEffect(() => {
    if (hasTimeEnded && typeof onTimeUp === 'function') {
      onTimeUp();
    }
  }, [hasTimeEnded, onTimeUp]);

  return (
    <div className={`countdown-container ${isGracePeriod ? 'grace-period' : ''}`}>
      <div className="mb-2 text-sm font-semibold">
        {hasTimeEnded ? "Submissions Closed" : (isGracePeriod ? "Grace Period Remaining" : "Time Remaining")}
      </div>
      {hasTimeEnded ? (
        <div className="font-mono text-lg">Time's up!</div>
      ) : (
        <div className="countdown-timer">
          <TimeBlock value={timeLeft.days || 0} label="Days" />
          <TimeBlock value={timeLeft.hours || 0} label="Hours" />
          <TimeBlock value={timeLeft.minutes || 0} label="Mins" />
          <TimeBlock value={timeLeft.seconds || 0} label="Secs" />
        </div>
      )}
    </div>
  );
}

export default CountdownTimer;