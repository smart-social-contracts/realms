// src/lib/stores/profiles.ts
import { writable, derived, get } from 'svelte/store';
import type { Readable } from 'svelte/store';

// Add type assertions for imports from JavaScript files
// @ts-ignore
import { isAuthenticated } from './auth';

// Type for backend response
interface BackendResponse {
    success: boolean;
    data?: {
        userGet?: {
            principal: string;
            profiles: string[];
        };
    };
}

// Define a type for profile state
interface ProfileState {
    profiles: string[];
    loading: boolean;
    error: string | null;
}

// Create a more comprehensive store for profiles with loading and error states
const profileState = writable<ProfileState>({
    profiles: [],
    loading: false,
    error: null
});

// Derived store for just the profiles array for backward compatibility
export const userProfiles = derived(
    profileState,
    $state => $state.profiles
);

// Derived store for the loading state
export const profilesLoading = derived(
    profileState,
    $state => $state.loading
);

// Derived store for the error state
export const profilesError = derived(
    profileState,
    $state => $state.error
);

// Helper function to check if user has a specific profile
export function hasProfile(profile: string): boolean {
    const state = get(profileState);
    
    // If we're still loading profiles, we can't determine if the user has the profile
    if (state.loading) {
        console.log("Profiles still loading, can't determine if user has profile:", profile);
        return false;
    }
    

    return Array.isArray(state.profiles) && state.profiles.includes(profile);
}

// Helper function to check if user has admin profile
export function isAdmin(): boolean {
    return hasProfile('admin');
}

// Helper function to check if user has member profile
export function isMember(): boolean {
    return hasProfile('member');
}

export function hasJoined(): boolean {
    const state = get(profileState);
    // Don't return false while still loading - defer the decision
    if (state.loading && get(isAuthenticated)) {
        return true; // Optimistically assume the user has joined while loading if they're authenticated
    }
    return hasProfile('member') || hasProfile('admin');
}

// Reset profile state back to initial values
export function resetProfileState(): void {
    profileState.set({
        profiles: [],
        loading: false,
        error: null
    });
}

export function setProfilesForTesting(profiles: string[]): void {
    profileState.update(state => ({
        ...state,
        profiles,
        loading: false,
        error: null
    }));
}

// Centralized function to load user profiles
export async function loadUserProfiles() {
    // Skip if not authenticated
    if (!get(isAuthenticated)) {
        return;
    }
    
    // Set loading state
    profileState.update(state => ({
        ...state,
        loading: true,
        error: null
    }));
    
    try {
        // Dynamically import backend to avoid circular dependencies
        // @ts-ignore
        const { backend } = await import('$lib/canisters');
        
        if (!backend || typeof backend.get_my_user_status !== 'function') {
            throw new Error("Backend canister is not properly initialized");
        }
        
        const response = await backend.get_my_user_status();

        console.log("User profiles response:", response);
        
        if (response && response.success && response.data && response.data.userGet) {
            const profiles = response.data.userGet.profiles || [];
            profileState.update(state => ({
                ...state,
                profiles,
                loading: false
            }));
            console.log("User profiles loaded:", profiles);
        } else {
            console.error("Invalid backend response format:", response);
            throw new Error('Invalid response format');
        }
    } catch (e: unknown) {
        const errorMessage = e instanceof Error ? e.message : 'Unknown error loading profiles';
        console.error("Error loading user profiles:", e);
        profileState.update(state => ({
            ...state,
            loading: false,
            error: errorMessage
        }));
    }
}
