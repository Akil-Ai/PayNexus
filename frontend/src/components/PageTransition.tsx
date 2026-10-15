import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Premium fintech page transition wrapper:
 * Outgoing page: Fade out smoothly, move upward 8-12px.
 * Incoming page: Starts with reduced opacity, moves upward gently into normal position, finishes crisp.
 * Respects prefers-reduced-motion.
 */
export const PageTransition: React.FC<PageTransitionProps> = ({ children, className = '' }) => {
  const shouldReduceMotion = useReducedMotion();

  const pageVariants = {
    initial: shouldReduceMotion
      ? { opacity: 0 }
      : { opacity: 0, y: 12 },
    animate: shouldReduceMotion
      ? { opacity: 1 }
      : {
          opacity: 1,
          y: 0,
          transition: {
            duration: 0.28,
            ease: [0.22, 1, 0.36, 1], // Natural easeOutCubic
            when: 'beforeChildren',
          },
        },
    exit: shouldReduceMotion
      ? { opacity: 0 }
      : {
          opacity: 0,
          y: -10,
          transition: {
            duration: 0.16,
            ease: [0.4, 0, 1, 1], // Snappy easeIn
          },
        },
  };

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={`w-full min-h-full ${className}`}
    >
      {children}
    </motion.div>
  );
};
