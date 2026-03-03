'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, UserData } from './api';

interface AuthState {
    user: UserData | null;
    token: string | null;
    isLoading: boolean;
}

interface AuthContextType extends AuthState {
    login: (email: string, password: string) => Promise<void>;
    signup: (username: string, email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<AuthState>({
        user: null,
        token: null,
        isLoading: true,
    });

    // Restore token from localStorage on mount
    useEffect(() => {
        const token = localStorage.getItem('audioshield_token');
        const userData = localStorage.getItem('audioshield_user');
        if (token && userData) {
            api.setToken(token);
            setState({
                user: JSON.parse(userData),
                token,
                isLoading: false,
            });
        } else {
            setState((s) => ({ ...s, isLoading: false }));
        }
    }, []);

    const login = async (email: string, password: string) => {
        const res = await api.login(email, password);
        localStorage.setItem('audioshield_token', res.access_token);
        localStorage.setItem('audioshield_user', JSON.stringify(res.user));
        api.setToken(res.access_token);
        setState({ user: res.user, token: res.access_token, isLoading: false });
    };

    const signup = async (username: string, email: string, password: string) => {
        const res = await api.signup(username, email, password);
        localStorage.setItem('audioshield_token', res.access_token);
        localStorage.setItem('audioshield_user', JSON.stringify(res.user));
        api.setToken(res.access_token);
        setState({ user: res.user, token: res.access_token, isLoading: false });
    };

    const logout = () => {
        localStorage.removeItem('audioshield_token');
        localStorage.removeItem('audioshield_user');
        api.setToken(null);
        setState({ user: null, token: null, isLoading: false });
    };

    return (
        <AuthContext.Provider value={{ ...state, login, signup, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
