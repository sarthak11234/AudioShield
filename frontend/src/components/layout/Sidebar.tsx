'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { LayoutDashboard, Upload, Archive, Settings, Shield, LogOut } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

const navItems = [
    { href: '/', icon: LayoutDashboard, label: 'Overview' },
    { href: '/protect', icon: Upload, label: 'Protect New' },
    { href: '/vault', icon: Archive, label: 'My Vault' },
    { href: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    return (
        <aside className="glass-sidebar h-screen w-64 fixed left-0 top-0 flex flex-col py-6 px-4">
            {/* Logo */}
            <div className="flex items-center gap-3 px-2 mb-10">
                <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center glow-indigo">
                    <Shield className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-[#6C5CE7] to-[#00CEC9] bg-clip-text text-transparent">
                    AudioShield
                </span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-2">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link key={item.href} href={item.href}>
                            <motion.div
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${isActive
                                    ? 'bg-white/10 text-white'
                                    : 'text-white/60 hover:text-white hover:bg-white/5'
                                    }`}
                                whileHover={{ x: 4 }}
                                whileTap={{ scale: 0.98 }}
                            >
                                <item.icon className="w-5 h-5" />
                                <span className="font-medium">{item.label}</span>
                                {isActive && (
                                    <motion.div
                                        layoutId="activeNav"
                                        className="absolute left-0 w-1 h-8 bg-gradient-to-b from-[#6C5CE7] to-[#00CEC9] rounded-r-full"
                                    />
                                )}
                            </motion.div>
                        </Link>
                    );
                })}
            </nav>

            {/* User Info & Logout */}
            {user && (
                <div className="border-t border-white/10 pt-4 space-y-3">
                    <div className="px-2">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full gradient-primary flex items-center justify-center text-sm font-bold">
                                {user.username.charAt(0).toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">{user.username}</p>
                                <p className="text-xs text-white/40 truncate">{user.email}</p>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className="flex items-center gap-3 px-4 py-2 rounded-xl text-white/40 hover:text-[#FF7675] hover:bg-white/5 transition-colors w-full"
                    >
                        <LogOut className="w-4 h-4" />
                        <span className="text-sm">Sign out</span>
                    </button>
                </div>
            )}
        </aside>
    );
}
