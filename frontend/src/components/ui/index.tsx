'use client';

import { motion } from 'framer-motion';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export function GlassPanel({ children, className = '', hover = false }: GlassPanelProps) {
  return (
    <motion.div
      className={`glass-panel p-6 relative overflow-hidden ${className}`}
      whileHover={hover ? { 
        scale: 1.015, 
        boxShadow: '0 4px 30px rgba(124, 58, 237, 0.12), 0 2px 8px rgba(0,0,0,0.05)',
      } : {}}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'ghost';
  className?: string;
  disabled?: boolean;
}

export function Button({ children, onClick, variant = 'primary', className = '', disabled }: ButtonProps) {
  const variants = {
    primary: 'btn-primary glow-violet',
    secondary: 'bg-transparent border border-[rgba(124,58,237,0.2)] text-[var(--text-primary)] px-6 py-3 rounded-2xl hover:bg-[rgba(124,58,237,0.05)] hover:border-[var(--violet)] transition-all duration-250',
    ghost: 'bg-transparent text-[var(--text-secondary)] px-6 py-3 rounded-2xl hover:text-[var(--text-primary)] hover:bg-[rgba(124,58,237,0.04)] transition-all duration-250',
  };

  return (
    <motion.button
      className={`${variants[variant]} ${className} ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
      onClick={onClick}
      disabled={disabled}
      whileHover={!disabled ? { scale: 1.02 } : {}}
      whileTap={!disabled ? { scale: 0.97 } : {}}
    >
      {children}
    </motion.button>
  );
}

interface BadgeProps {
  status: 'secure' | 'vulnerable' | 'processing';
  children: React.ReactNode;
}

export function Badge({ status, children }: BadgeProps) {
  const classes = {
    secure: 'badge-secure',
    vulnerable: 'badge-vulnerable',
    processing: 'badge-processing',
  };

  return <span className={classes[status]}>{children}</span>;
}
