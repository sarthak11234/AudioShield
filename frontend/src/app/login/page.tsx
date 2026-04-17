'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Shield, Mail, Lock, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';

export default function LoginPage() {
    const router = useRouter();
    const { login } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email, password);
            router.push('/');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            {/* Mesh gradient background */}
            <div className="fixed inset-0 bg-[var(--bg-deepest)]" />
            <div className="fixed top-[15%] left-[20%] w-[500px] h-[500px] bg-[rgba(124,58,237,0.07)] rounded-full blur-[120px] animate-glow-pulse" />
            <div className="fixed bottom-[20%] right-[15%] w-[400px] h-[400px] bg-[rgba(99,102,241,0.06)] rounded-full blur-[100px] animate-glow-pulse" style={{ animationDelay: '1.5s' }} />
            <div className="fixed top-[60%] left-[60%] w-[300px] h-[300px] bg-[rgba(167,139,250,0.04)] rounded-full blur-[80px]" />

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="relative z-10 w-full max-w-md"
            >
                {/* Logo */}
                <div className="text-center mb-8">
                    <motion.div 
                        className="w-16 h-16 mx-auto mb-5 rounded-2xl gradient-primary flex items-center justify-center glow-violet"
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
                    >
                        <Shield className="w-8 h-8 text-white" />
                    </motion.div>
                    <h1 className="text-3xl font-bold gradient-text tracking-tight">
                        AudioShield
                    </h1>
                    <p className="text-[var(--text-muted)] mt-1.5 text-sm">Protect your voice from AI</p>
                </div>

                {/* Form Card */}
                <div className="glass-panel p-8">
                    <h2 className="text-xl font-semibold mb-6 tracking-tight">Welcome back</h2>

                    {error && (
                        <motion.div 
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-[rgba(244,63,94,0.06)] border border-[rgba(244,63,94,0.15)] text-[var(--rose)] px-4 py-3 rounded-xl mb-4 text-sm"
                        >
                            {error}
                        </motion.div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="text-sm text-[var(--text-muted)] mb-1.5 block">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@artist.com"
                                    required
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-sm text-[var(--text-muted)] mb-1.5 block">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <motion.button
                            type="submit"
                            disabled={loading}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.97 }}
                            className="w-full gradient-primary text-white font-semibold py-3 rounded-2xl flex items-center justify-center gap-2 glow-violet disabled:opacity-40 transition-all"
                        >
                            {loading ? 'Signing in...' : 'Sign In'}
                            {!loading && <ArrowRight className="w-4 h-4" />}
                        </motion.button>
                    </form>

                    <p className="text-center text-[var(--text-muted)] text-sm mt-6">
                        Don&apos;t have an account?{' '}
                        <Link href="/signup" className="text-[var(--violet)] hover:text-[var(--violet-deep)] transition-colors font-medium">
                            Sign up
                        </Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
