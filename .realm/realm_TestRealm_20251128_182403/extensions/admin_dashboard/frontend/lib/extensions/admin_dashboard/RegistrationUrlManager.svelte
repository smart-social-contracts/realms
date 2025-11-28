<script>
    import { onMount } from 'svelte';
    import { backend } from '$lib/canisters';

    let userId = '';
    let email = '';
    let expiresInHours = 24;
    let frontendUrl = window.location.origin;
    let generatedUrl = '';
    let registrationCodes = [];
    let loading = false;
    let error = '';
    let success = '';

    onMount(() => {
        loadRegistrationCodes();
    });

    async function generateRegistrationUrl() {
        if (!userId.trim()) {
            error = 'User ID is required';
            return;
        }

        loading = true;
        error = '';
        success = '';

        try {
            const response = await backend.extension_sync_call({
                extension_name: 'admin_dashboard',
                function_name: 'generate_registration_url',
                args: JSON.stringify({
                    user_id: userId,
                    email: email || null,
                    expires_in_hours: parseInt(expiresInHours),
                    frontend_url: frontendUrl,
                    created_by: 'admin' // TODO: Get actual admin user ID
                })
            });
            
            let result;
            try {
                result = JSON.parse(response.response);
            } catch (e) {
                console.error('Failed to parse registration URL response:', e);
                error = 'Invalid response format from server';
                return;
            }

            if (result.success) {
                generatedUrl = result.data.registration_url;
                success = 'Registration URL generated successfully!';
                await loadRegistrationCodes();
                // Clear form
                userId = '';
                email = '';
            } else {
                error = result.error || 'Failed to generate registration URL';
            }
        } catch (e) {
            error = 'Network error: ' + e.message;
        } finally {
            loading = false;
        }
    }

    async function loadRegistrationCodes() {
        try {
            const response = await backend.extension_sync_call({
                extension_name: 'admin_dashboard',
                function_name: 'get_registration_codes',
                args: JSON.stringify({
                    include_used: true
                })
            });

            let result;
            try {
                result = JSON.parse(response.response);
                if (result.success) {
                    registrationCodes = result.data;
                }
            } catch (e) {
                console.error('Failed to parse registration codes response:', e);
                error = 'Invalid response format from server';
            }
        } catch (e) {
            console.error('Failed to load registration codes:', e);
        }
    }

    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            success = 'URL copied to clipboard!';
            setTimeout(() => success = '', 3000);
        });
    }

    function formatDate(isoString) {
        return new Date(isoString).toLocaleString();
    }
</script>

<div class="registration-url-manager">
    <h2>Registration URL Management</h2>

    <!-- Generate New URL Form -->
    <div class="form-section">
        <h3>Generate New Registration URL</h3>
        
        <div class="form-group">
            <label for="userId">User ID *</label>
            <input
                id="userId"
                type="text"
                bind:value={userId}
                placeholder="Enter user ID"
                disabled={loading}
            />
        </div>

        <div class="form-group">
            <label for="email">Email (optional)</label>
            <input
                id="email"
                type="email"
                bind:value={email}
                placeholder="user@example.com"
                disabled={loading}
            />
        </div>

        <div class="form-group">
            <label for="expires">Expires in (hours)</label>
            <input
                id="expires"
                type="number"
                bind:value={expiresInHours}
                min="1"
                max="168"
                disabled={loading}
            />
        </div>

        <div class="form-group">
            <label for="frontendUrl">Frontend URL</label>
            <input
                id="frontendUrl"
                type="url"
                bind:value={frontendUrl}
                disabled={loading}
            />
        </div>

        <button
            class="btn-primary"
            on:click={generateRegistrationUrl}
            disabled={loading || !userId.trim()}
        >
            {loading ? 'Generating...' : 'Generate Registration URL'}
        </button>

        {#if error}
            <div class="alert alert-error">{error}</div>
        {/if}

        {#if success}
            <div class="alert alert-success">{success}</div>
        {/if}

        {#if generatedUrl}
            <div class="generated-url">
                <h4>Generated URL:</h4>
                <div class="url-container">
                    <input
                        type="text"
                        value={generatedUrl}
                        readonly
                        class="url-input"
                    />
                    <button
                        class="btn-copy"
                        on:click={() => copyToClipboard(generatedUrl)}
                    >
                        Copy
                    </button>
                </div>
            </div>
        {/if}
    </div>

    <!-- Registration Codes List -->
    <div class="codes-section">
        <h3>Existing Registration Codes</h3>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Email</th>
                        <th>Code</th>
                        <th>Expires</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {#each registrationCodes as code}
                        <tr class:expired={!code.is_valid} class:used={code.used}>
                            <td>{code.user_id}</td>
                            <td>{code.email || '-'}</td>
                            <td class="code-cell">{code.code}</td>
                            <td>{formatDate(code.expires_at)}</td>
                            <td>
                                <span class="status-badge" class:valid={code.is_valid} class:invalid={!code.is_valid}>
                                    {code.used ? 'Used' : code.is_valid ? 'Valid' : 'Expired'}
                                </span>
                            </td>
                            <td>
                                <button
                                    class="btn-small"
                                    on:click={() => copyToClipboard(code.registration_url)}
                                >
                                    Copy URL
                                </button>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    </div>
</div>

<style>
    .registration-url-manager {
        padding: 20px;
        max-width: 1200px;
        margin: 0 auto;
    }

    .form-section, .codes-section {
        background: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .form-group {
        margin-bottom: 15px;
    }

    label {
        display: block;
        margin-bottom: 5px;
        font-weight: 500;
    }

    input {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
    }

    input:disabled {
        background-color: #f5f5f5;
    }

    .btn-primary {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    }

    .btn-primary:hover:not(:disabled) {
        background-color: #0056b3;
    }

    .btn-primary:disabled {
        background-color: #6c757d;
        cursor: not-allowed;
    }

    .btn-copy, .btn-small {
        background-color: #28a745;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 3px;
        cursor: pointer;
        font-size: 12px;
    }

    .btn-copy:hover, .btn-small:hover {
        background-color: #218838;
    }

    .alert {
        padding: 10px;
        border-radius: 4px;
        margin-top: 10px;
    }

    .alert-error {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    .alert-success {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }

    .generated-url {
        margin-top: 20px;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 4px;
    }

    .url-container {
        display: flex;
        gap: 10px;
        margin-top: 10px;
    }

    .url-input {
        flex: 1;
        font-family: monospace;
    }

    .table-container {
        overflow-x: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }

    th, td {
        padding: 10px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }

    th {
        background-color: #f8f9fa;
        font-weight: 600;
    }

    .code-cell {
        font-family: monospace;
        font-size: 12px;
    }

    .status-badge {
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
    }

    .status-badge.valid {
        background-color: #d4edda;
        color: #155724;
    }

    .status-badge.invalid {
        background-color: #f8d7da;
        color: #721c24;
    }

    tr.expired {
        opacity: 0.6;
    }

    tr.used {
        background-color: #f8f9fa;
    }
</style>
