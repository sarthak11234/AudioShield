'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import { Sidebar } from './Sidebar';

const PUBLIC_ROUTES = ['/login', '/signup'];

function AuthGate({ children }: { children: React.ReactNode }) {
    const { user, isLoading } = useAuth();
    const pathname = usePathname();
    const router = useRouter();
    const isPublic = PUBLIC_ROUTES.includes(pathname);

    useEffect(() => {
        if (!isLoading && !user && !isPublic) {
            router.push('/login');
        }
        if (!isLoading && user && isPublic) {
            router.push('/');
        }
    }, [user, isLoading, isPublic, router]);

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-[#6C5CE7] border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user && !isPublic) return null;

    if (isPublic) {
        return <>{children}</>;
    }

    return (
        <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-64 p-8">
                {children}
            </main>
        </div>
    );
}

export function AppShell({ children }: { children: React.ReactNode }) {
    return (
        <AuthProvider>
            <AuthGate>{children}</AuthGate>
        </AuthProvider>
    );
}
