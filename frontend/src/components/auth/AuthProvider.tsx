"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserProfile, apiFetch, clearStoredTokens, getStoredToken, setStoredTokens } from "@/lib/auth";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (tokens: { access_token: string; refresh_token: string }, user: UserProfile) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      const data = await apiFetch<UserProfile>("/auth/me");
      setUser(data);
      if (typeof window !== "undefined") {
        localStorage.setItem("udyamsetu_user", JSON.stringify(data));
      }
    } catch (err) {
      console.warn("Failed to fetch authenticated profile:", err);
      clearStoredTokens();
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const savedToken = getStoredToken();
    if (savedToken) {
      setToken(savedToken);
      fetchProfile();
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = (tokens: { access_token: string; refresh_token: string }, profile: UserProfile) => {
    setStoredTokens(tokens);
    setToken(tokens.access_token);
    setUser(profile);
    if (typeof window !== "undefined") {
      localStorage.setItem("udyamsetu_user", JSON.stringify(profile));
    }
  };

  const logout = () => {
    clearStoredTokens();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        refreshUser: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
