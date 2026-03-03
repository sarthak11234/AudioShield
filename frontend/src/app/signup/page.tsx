'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Shield, Mail, Lock, User, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';

export default function SignupPage() {
    const router = useRouter();
    const { signup } = useAuth();
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await signup(username, email, password);
            router.push('/');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Signup failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            {/* Background gradient */}
            <div className="fixed inset-0 bg-gradient-to-br from-[#0a0a1a] via-[#0f0f2d] to-[#0a0a1a]" />
            <div className="fixed top-1/3 right-1/4 w-96 h-96 bg-[#00CEC9]/10 rounded-full blur-3xl" />
            <div className="fixed bottom-1/3 left-1/4 w-96 h-96 bg-[#6C5CE7]/10 rounded-full blur-3xl" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative z-10 w-full max-w-md"
            >
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl gradient-primary flex items-center justify-center glow-indigo">
                        <Shield className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-[#6C5CE7] to-[#00CEC9] bg-clip-text text-transparent">
                        Join AudioShield
                    </h1>
                    <p className="text-white/50 mt-1">Start protecting your audio today</p>
                </div>

                {/* Form Card */}
                <div className="glass-panel p-8 rounded-2xl">
                    <h2 className="text-xl font-semibold mb-6">Create your account</h2>

                    {error && (
                        <div className="bg-[#FF7675]/10 border border-[#FF7675]/30 text-[#FF7675] px-4 py-3 rounded-xl mb-4 text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="text-sm text-white/60 mb-1 block">Artist Name</label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Your artist name"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#6C5CE7] transition-colors"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-sm text-white/60 mb-1 block">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@artist.com"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#6C5CE7] transition-colors"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-sm text-white/60 mb-1 block">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    minLength={6}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#6C5CE7] transition-colors"
                                />
                            </div>
                        </div>

                        <motion.button
                            type="submit"
                            disabled={loading}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="w-full gradient-primary text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 glow-indigo disabled:opacity-50"
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                            {!loading && <ArrowRight className="w-4 h-4" />}
                        </motion.button>
                    </form>

                    <p className="text-center text-white/40 text-sm mt-6">
                        Already have an account?{' '}
                        <Link href="/login" className="text-[#6C5CE7] hover:text-[#00CEC9] transition-colors font-medium">
                            Sign in
                        </Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
