import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

const SwipeAnimation = () => {
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    // Start animation after initial delay
    const startTimer = setTimeout(() => {
      setIsAnimating(true);
    }, 500);

    return () => clearTimeout(startTimer);
  }, []);

  useEffect(() => {
    if (isAnimating) {
      // Reset animation after completion + pause
      const resetTimer = setTimeout(() => {
        setIsAnimating(false);
        // Start next loop
        setTimeout(() => {
          setIsAnimating(true);
        }, 1200);
      }, 3000);

      return () => clearTimeout(resetTimer);
    }
  }, [isAnimating]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-secondary/30">
      <div className="relative flex items-center gap-4">
        {/* Arrow Icon Container - glides across the text */}
        <div
          className={`relative z-20 transition-all duration-[3000ms] ${
            isAnimating ? "translate-x-[420px]" : "translate-x-0"
          }`}
          style={{ transitionTimingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
        >
          <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-primary shadow-[0_20px_60px_-15px_hsl(208_100%_56%/0.4)]">
            <ArrowRight className="h-12 w-12 text-primary-foreground" strokeWidth={3} />
          </div>
        </div>

        {/* Swipr Text with enhanced delete effects */}
        <div className="absolute left-28 top-1/2 -translate-y-1/2 overflow-hidden">
          <h1 
            className={`text-8xl font-bold tracking-tight text-primary transition-all duration-[3000ms] ${
              isAnimating ? "opacity-0 scale-90 blur-sm" : "opacity-100 scale-100 blur-0"
            }`}
            style={{ transitionTimingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
          >
            Swipr
          </h1>
          
          {/* Overlay that reveals as arrow moves - creating delete effect */}
          <div
            className={`absolute left-0 top-0 h-full bg-gradient-to-r from-background/80 via-background/60 to-transparent transition-all duration-[3000ms] ${
              isAnimating ? "w-full" : "w-0"
            }`}
            style={{ transitionTimingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
          />
        </div>

        {/* Enhanced glow effect following the arrow */}
        <div
          className={`absolute left-0 top-1/2 -translate-y-1/2 h-32 w-40 bg-primary/30 blur-3xl transition-all duration-[3000ms] ${
            isAnimating ? "translate-x-[420px] opacity-0" : "translate-x-0 opacity-100"
          }`}
          style={{ transitionTimingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
        />
        
        {/* Additional shimmer trail */}
        <div
          className={`absolute left-20 top-1/2 -translate-y-1/2 h-24 w-24 bg-gradient-to-r from-transparent via-primary/20 to-transparent blur-xl transition-all duration-[3000ms] ${
            isAnimating ? "translate-x-[420px]" : "translate-x-0"
          }`}
          style={{ transitionTimingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
        />
      </div>
    </div>
  );
};

export default SwipeAnimation;
