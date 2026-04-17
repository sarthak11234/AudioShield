'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Upload, Archive, Settings, Shield, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

const navItems = [
    { href: '/', icon: LayoutDashboard, label: 'Overview' },
    { href: '/protect', icon: Upload, label: 'Protect New' },
    { href: '/vault', icon: Archive, label: 'My Vault' },
    { href: '/settings', icon: Settings, label: 'Settings' },
];

interface SidebarProps {
    isCollapsed: boolean;
    setIsCollapsed: (cls: boolean) => void;
}

export function Sidebar({ isCollapsed, setIsCollapsed }: SidebarProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    return (
        <motion.aside 
            className="glass-sidebar h-screen fixed left-0 top-0 flex flex-col py-6 z-50 overflow-hidden"
            initial={{ width: 256 }}
            animate={{ width: isCollapsed ? 80 : 256, paddingLeft: isCollapsed ? 8 : 20, paddingRight: isCollapsed ? 8 : 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
            {/* Logo */}
            <div className={`flex items-center gap-3 px-2 mb-10 ${isCollapsed ? 'justify-center' : ''}`}>
                <div className="min-w-[42px] h-[42px] rounded-2xl gradient-primary flex items-center justify-center glow-violet">
                    <Shield className="w-5 h-5 text-white" />
                </div>
                <AnimatePresence>
                    {!isCollapsed && (
                        <motion.span
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: 'auto' }}
                            exit={{ opacity: 0, width: 0 }}
                            className="text-xl font-bold gradient-text whitespace-nowrap overflow-hidden tracking-tight"
                        >
                            AudioShield
                        </motion.span>
                    )}
                </AnimatePresence>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1.5">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link key={item.href} href={item.href}>
                            <motion.div
                                className={`relative flex items-center gap-3 py-3 rounded-xl transition-all duration-200 ${
                                    isCollapsed ? 'justify-center px-0' : 'px-4'
                                } ${isActive
                                    ? 'bg-[rgba(124,58,237,0.1)] text-[var(--violet)]'
                                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[rgba(124,58,237,0.05)]'
                                    }`}
                                whileHover={{ x: isCollapsed ? 0 : 3 }}
                                whileTap={{ scale: 0.97 }}
                            >
                                <item.icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-[var(--violet)]' : ''}`} />
                                <AnimatePresence>
                                    {!isCollapsed && (
                                        <motion.span 
                                            initial={{ opacity: 0, width: 0 }}
                                            animate={{ opacity: 1, width: 'auto' }}
                                            exit={{ opacity: 0, width: 0 }}
                                            className="font-medium whitespace-nowrap overflow-hidden text-sm"
                                        >
                                            {item.label}
                                        </motion.span>
                                    )}
                                </AnimatePresence>
                                {isActive && (
                                    <motion.div
                                        layoutId="activeNav"
                                        className="absolute left-0 w-[3px] h-7 bg-gradient-to-b from-[var(--purple-soft)] to-[var(--violet)] rounded-r-full"
                                    />
                                )}
                            </motion.div>
                        </Link>
                    );
                })}
            </nav>

            {/* Collapse Toggle */}
            <div className="mb-4 hidden md:flex px-2">
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="flex items-center justify-center w-full py-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--violet)] hover:bg-[rgba(124,58,237,0.05)] transition-all duration-200"
                >
                    {isCollapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
                </button>
            </div>

            {/* User Info & Logout */}
            {user && (
                <div className={`border-t border-[var(--glass-border)] pt-4 space-y-3 ${isCollapsed ? 'items-center flex flex-col' : ''}`}>
                    <div className="px-2">
                        <div className={`flex items-center gap-3 ${isCollapsed ? 'justify-center' : ''}`}>
                            <div className="w-9 h-9 flex-shrink-0 rounded-full gradient-primary flex items-center justify-center text-sm font-bold text-white ring-2 ring-[rgba(124,58,237,0.2)] ring-offset-2 ring-offset-white">
                                {user.username.charAt(0).toUpperCase()}
                            </div>
                            <AnimatePresence>
                                {!isCollapsed && (
                                    <motion.div 
                                        initial={{ opacity: 0, width: 0 }}
                                        animate={{ opacity: 1, width: 'auto' }}
                                        exit={{ opacity: 0, width: 0 }}
                                        className="flex-1 min-w-0 overflow-hidden"
                                    >
                                        <p className="text-sm font-medium truncate text-[var(--text-primary)]">{user.username}</p>
                                        <p className="text-xs text-[var(--text-muted)] truncate">{user.email}</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className={`flex items-center gap-3 py-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--rose)] hover:bg-[rgba(244,63,94,0.06)] transition-all duration-200 w-full ${isCollapsed ? 'justify-center' : 'px-4'}`}
                        title={isCollapsed ? "Sign out" : ""}
                    >
                        <LogOut className="w-4 h-4 flex-shrink-0" />
                        <AnimatePresence>
                            {!isCollapsed && (
                                <motion.span 
                                    initial={{ opacity: 0, width: 0 }}
                                    animate={{ opacity: 1, width: 'auto' }}
                                    exit={{ opacity: 0, width: 0 }}
                                    className="text-sm whitespace-nowrap overflow-hidden"
                                >
                                    Sign out
                                </motion.span>
                            )}
                        </AnimatePresence>
                    </button>
                </div>
            )}
        </motion.aside>
    );
}
