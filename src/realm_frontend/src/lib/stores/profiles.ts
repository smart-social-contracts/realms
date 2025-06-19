// src/lib/stores/profiles.ts
import { writable } from 'svelte/store';

// Store for user profiles (admin, member)
export const userProfiles = writable<string[]>([]);

// Helper function to check if user has a specific profile
export function hasProfile(profile: string): boolean {
    let profiles: string[] = [];
    userProfiles.subscribe(value => {
        profiles = value;
    })();
    
    return Array.isArray(profiles) && profiles.includes(profile);
}

// Helper function to check if user has admin profile
export function isAdmin(): boolean {
    return hasProfile('admin');
}

// Helper function to check if user has member profile
export function isMember(): boolean {
    return hasProfile('member');
}
