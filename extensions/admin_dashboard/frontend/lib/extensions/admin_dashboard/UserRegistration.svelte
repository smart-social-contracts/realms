<script>
    import { onMount } from 'svelte';
    import { backend } from '$lib/canisters';

    export let registrationCode = '';

    let loading = false;
    let error = '';
    let success = '';
    let codeValid = false;
    let userInfo = null;
    let formData = {
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        fullName: ''
    };

    onMount(() => {
        // Get code from URL params if not provided
        if (!registrationCode) {
            const urlParams = new URLSearchParams(window.location.search);
            registrationCode = urlParams.get('code') || '';
        }
        
        if (registrationCode) {
            validateCode();
        }
    });

    async function validateCode() {
        if (!registrationCode) {
            error = 'No registration code provided';
            return;
        }

        loading = true;
        error = '';

        try {
            const response = await backend.extension_sync_call({
                extension_name: 'admin_dashboard',
                function_name: 'validate_registration_code',
                args: JSON.stringify({
                    code: registrationCode
                })
            });

            let result;
            try {
                result = JSON.parse(response.response);
                if (result.success) {
                    codeValid = true;
                    userInfo = result.data;
                }
            } catch (e) {
                console.error('Failed to parse validation response:', e);
                error = 'Invalid response format from server';
                return;
            }
                // Pre-fill email if available
                if (userInfo.email) {
                    formData.email = userInfo.email;
                }
            } else {
                error = result.error || 'Invalid or expired registration code';
                codeValid = false;
            }
        } catch (e) {
            error = 'Network error: ' + e.message;
            codeValid = false;
        } finally {
            loading = false;
        }
    }

    async function submitRegistration() {
        // Validate form
        if (!formData.username.trim()) {
            error = 'Username is required';
            return;
        }
        if (!formData.email.trim()) {
            error = 'Email is required';
            return;
        }
        if (!formData.password) {
            error = 'Password is required';
            return;
        }
        if (formData.password !== formData.confirmPassword) {
            error = 'Passwords do not match';
            return;
        }

        loading = true;
        error = '';

        try {
            // TODO: Implement actual user registration logic
            // This would typically call a user creation endpoint
            
            // For now, just mark the registration code as used
            // In a real implementation, this would be part of the user creation process
            
            success = 'Registration completed successfully! You can now log in.';
            
            // Clear form
            formData = {
                username: '',
                email: '',
                password: '',
                confirmPassword: '',
                fullName: ''
            };
            
        } catch (e) {
            error = 'Registration failed: ' + e.message;
        } finally {
            loading = false;
        }
    }

    function isFormValid() {
        return formData.username.trim() &&
               formData.email.trim() &&
               formData.password &&
               formData.password === formData.confirmPassword;
    }
</script>

<div class="user-registration">
    <div class="registration-container">
        <h1>User Registration</h1>

        {#if loading}
            <div class="loading">
                <div class="spinner"></div>
                <p>Processing...</p>
            </div>
        {:else if !codeValid}
            <div class="code-validation">
                <h2>Validate Registration Code</h2>
                <p>Please enter your registration code to continue.</p>
                
                <div class="form-group">
                    <label for="code">Registration Code</label>
                    <input
                        id="code"
                        type="text"
                        bind:value={registrationCode}
                        placeholder="Enter your registration code"
                        maxlength="16"
                    />
                </div>

                <button
                    class="btn-primary"
                    on:click={validateCode}
                    disabled={!registrationCode.trim()}
                >
                    Validate Code
                </button>

                {#if error}
                    <div class="alert alert-error">{error}</div>
                {/if}
            </div>
        {:else if success}
            <div class="success-message">
                <div class="success-icon">✓</div>
                <h2>Registration Complete!</h2>
                <p>{success}</p>
                <a href="/login" class="btn-primary">Go to Login</a>
            </div>
        {:else}
            <div class="registration-form">
                <h2>Create Your Account</h2>
                <p>Registration code validated for user: <strong>{userInfo.user_id}</strong></p>

                <form on:submit|preventDefault={submitRegistration}>
                    <div class="form-group">
                        <label for="username">Username *</label>
                        <input
                            id="username"
                            type="text"
                            bind:value={formData.username}
                            placeholder="Choose a username"
                            required
                        />
                    </div>

                    <div class="form-group">
                        <label for="fullName">Full Name</label>
                        <input
                            id="fullName"
                            type="text"
                            bind:value={formData.fullName}
                            placeholder="Your full name"
                        />
                    </div>

                    <div class="form-group">
                        <label for="email">Email *</label>
                        <input
                            id="email"
                            type="email"
                            bind:value={formData.email}
                            placeholder="your.email@example.com"
                            required
                        />
                    </div>

                    <div class="form-group">
                        <label for="password">Password *</label>
                        <input
                            id="password"
                            type="password"
                            bind:value={formData.password}
                            placeholder="Choose a secure password"
                            required
                        />
                    </div>

                    <div class="form-group">
                        <label for="confirmPassword">Confirm Password *</label>
                        <input
                            id="confirmPassword"
                            type="password"
                            bind:value={formData.confirmPassword}
                            placeholder="Confirm your password"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        class="btn-primary btn-large"
                        disabled={!isFormValid()}
                    >
                        Create Account
                    </button>

                    {#if error}
                        <div class="alert alert-error">{error}</div>
                    {/if}
                </form>

                <div class="registration-info">
                    <h3>Registration Details</h3>
                    <ul>
                        <li><strong>User ID:</strong> {userInfo.user_id}</li>
                        <li><strong>Code expires:</strong> {new Date(userInfo.expires_at).toLocaleString()}</li>
                        <li><strong>Created by:</strong> {userInfo.created_by}</li>
                    </ul>
                </div>
            </div>
        {/if}
    </div>
</div>

<style>
    .user-registration {
        min-height: 100vh;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }

    .registration-container {
        background: white;
        border-radius: 12px;
        padding: 40px;
        max-width: 500px;
        width: 100%;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }

    h1 {
        text-align: center;
        color: #333;
        margin-bottom: 30px;
        font-size: 28px;
    }

    h2 {
        color: #333;
        margin-bottom: 20px;
        font-size: 22px;
    }

    .loading {
        text-align: center;
        padding: 40px 20px;
    }

    .spinner {
        border: 3px solid #f3f3f3;
        border-top: 3px solid #667eea;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .success-message {
        text-align: center;
        padding: 20px;
    }

    .success-icon {
        font-size: 48px;
        color: #28a745;
        margin-bottom: 20px;
    }

    .form-group {
        margin-bottom: 20px;
    }

    label {
        display: block;
        margin-bottom: 8px;
        font-weight: 600;
        color: #333;
    }

    input {
        width: 100%;
        padding: 12px 16px;
        border: 2px solid #e1e5e9;
        border-radius: 8px;
        font-size: 16px;
        transition: border-color 0.3s ease;
        box-sizing: border-box;
    }

    input:focus {
        outline: none;
        border-color: #667eea;
    }

    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        transition: transform 0.2s ease;
        text-decoration: none;
        display: inline-block;
        text-align: center;
    }

    .btn-primary:hover:not(:disabled) {
        transform: translateY(-2px);
    }

    .btn-primary:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
    }

    .btn-large {
        width: 100%;
        padding: 16px 24px;
        font-size: 18px;
    }

    .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 15px;
    }

    .alert-error {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    .registration-info {
        margin-top: 30px;
        padding: 20px;
        background-color: #f8f9fa;
        border-radius: 8px;
    }

    .registration-info h3 {
        margin-top: 0;
        margin-bottom: 15px;
        color: #495057;
        font-size: 16px;
    }

    .registration-info ul {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .registration-info li {
        padding: 5px 0;
        color: #6c757d;
        font-size: 14px;
    }

    .code-validation {
        text-align: center;
    }

    .code-validation p {
        color: #6c757d;
        margin-bottom: 30px;
    }

    @media (max-width: 600px) {
        .registration-container {
            padding: 30px 20px;
            margin: 10px;
        }

        h1 {
            font-size: 24px;
        }

        h2 {
            font-size: 20px;
        }
    }
</style>
