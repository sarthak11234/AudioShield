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
      className={`glass-panel p-6 ${className}`}
      whileHover={hover ? { scale: 1.02, boxShadow: '0 0 30px rgba(108, 92, 231, 0.3)' } : {}}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  className?: string;
  disabled?: boolean;
}

export function Button({ children, onClick, variant = 'primary', className = '', disabled }: ButtonProps) {
  const baseClasses = variant === 'primary' 
    ? 'btn-primary glow-indigo'
    : 'bg-transparent border border-white/20 text-white px-6 py-3 rounded-xl hover:bg-white/5';

  return (
    <motion.button
      className={`${baseClasses} ${className} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      onClick={onClick}
      disabled={disabled}
      whileHover={!disabled ? { scale: 1.02 } : {}}
      whileTap={!disabled ? { scale: 0.98 } : {}}
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
    processing: 'bg-cyan-500 text-black px-3 py-1 rounded-full text-xs font-semibold'
  };

  return <span className={classes[status]}>{children}</span>;
}
