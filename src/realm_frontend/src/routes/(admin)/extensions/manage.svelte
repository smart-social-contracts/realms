<script>
    import { onMount } from 'svelte';
    import { Card, Table, Spinner, Button, Toggle, Modal, Textarea } from 'flowbite-svelte';
    import { PuzzlePieceSolid, CogSolid, CheckCircleSolid, XCircleSolid, AlertCircleSolid } from 'flowbite-svelte-icons';
    import { backend } from '$lib/canisters';
    
    // Component state
    let extensions = [];
    let loading = true;
    let error = '';
    let successMessage = '';
    
    // Modal state for configuration
    let showConfigModal = false;
    let currentExtension = null;
    let configJson = '';
    let configError = '';
    let configLoading = false;
    
    onMount(async () => {
        await loadExtensions();
    });
    
    async function loadExtensions() {
        loading = true;
        error = '';
        successMessage = '';
        
        try {
            // Call the backend API to get extension status
            const response = await backend.get_extension_status();
            
            if (response.success) {
                extensions = response.extensions;
                console.log('Loaded extensions:', extensions);
            } else {
                error = 'Failed to load extensions';
                console.error('Error loading extensions:', response);
            }
        } catch (e) {
            error = `Error: ${e.message}`;
            console.error('Exception loading extensions:', e);
        } finally {
            loading = false;
        }
    }
    
    async function toggleExtension(id, currentStatus) {
        try {
            // Update UI immediately to feel responsive
            const extensionIndex = extensions.findIndex(ext => ext.name === id);
            if (extensionIndex >= 0) {
                extensions[extensionIndex].enabled = !currentStatus;
                extensions = [...extensions]; // Trigger reactivity
            }
            
            // Call the backend API to update extension status
            const response = await backend.set_extension_status(id, !currentStatus);
            
            if (response.success) {
                successMessage = response.message;
                // Refresh the list to get the actual state
                await loadExtensions();
            } else {
                error = `Failed to update extension status: ${response.message}`;
                console.error('Error updating extension status:', response);
                // Revert UI change
                if (extensionIndex >= 0) {
                    extensions[extensionIndex].enabled = currentStatus;
                    extensions = [...extensions]; // Trigger reactivity
                }
            }
        } catch (e) {
            error = `Error: ${e.message}`;
            console.error('Exception updating extension status:', e);
            // Revert UI change
            const extensionIndex = extensions.findIndex(ext => ext.name === id);
            if (extensionIndex >= 0) {
                extensions[extensionIndex].enabled = currentStatus;
                extensions = [...extensions]; // Trigger reactivity
            }
        }
    }
    
    function openConfigModal(extension) {
        currentExtension = extension;
        // Convert settings to JSON for editing
        configJson = JSON.stringify(extension.settings || {}, null, 2);
        showConfigModal = true;
        configError = '';
    }
    
    async function saveConfig() {
        configLoading = true;
        configError = '';
        
        try {
            // Parse JSON
            const settings = JSON.parse(configJson);
            
            // Call the backend API to update extension config
            const response = await backend.set_extension_config(currentExtension.name, { settings });
            
            if (response.success) {
                successMessage = response.message;
                showConfigModal = false;
                // Refresh the list to get the updated state
                await loadExtensions();
            } else {
                configError = `Failed to update configuration: ${response.message}`;
                console.error('Error updating configuration:', response);
            }
        } catch (e) {
            if (e instanceof SyntaxError) {
                configError = 'Invalid JSON format. Please check your syntax.';
            } else {
                configError = `Error: ${e.message}`;
            }
            console.error('Exception updating configuration:', e);
        } finally {
            configLoading = false;
        }
    }
</script>

<svelte:head>
    <title>Manage Extensions</title>
</svelte:head>

<div class="container mx-auto p-4">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold flex items-center">
            <PuzzlePieceSolid class="mr-2 h-6 w-6 text-primary-600" />
            Extension Manager
        </h1>
        <Button color="primary" on:click={loadExtensions} disabled={loading}>
            {#if loading}
                <Spinner size="sm" class="mr-2" />
            {/if}
            Refresh
        </Button>
    </div>
    
    {#if error}
        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex items-start">
            <AlertCircleSolid class="mr-2 h-5 w-5 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
        </div>
    {/if}
    
    {#if successMessage}
        <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4 flex items-start">
            <CheckCircleSolid class="mr-2 h-5 w-5 flex-shrink-0 mt-0.5" />
            <span>{successMessage}</span>
        </div>
    {/if}
    
    <Card padding="lg" class="mb-6">
        <div class="text-sm text-gray-600 mb-4">
            <p>
                This page allows you to manage extensions installed in your realm. You can enable or disable extensions
                as needed, and configure their settings.
            </p>
            <p class="mt-2">
                Note: Some changes may require restarting the application to take full effect.
            </p>
        </div>
        
        {#if loading && extensions.length === 0}
            <div class="flex justify-center py-8">
                <Spinner size="xl" />
            </div>
        {:else if extensions.length === 0}
            <div class="text-center py-8 text-gray-500">
                <p>No extensions found</p>
            </div>
        {:else}
            <Table striped={true}>
                <Table.Head>
                    <Table.HeadCell>Name</Table.HeadCell>
                    <Table.HeadCell>Description</Table.HeadCell>
                    <Table.HeadCell>Permissions</Table.HeadCell>
                    <Table.HeadCell>Status</Table.HeadCell>
                    <Table.HeadCell>Actions</Table.HeadCell>
                </Table.Head>
                <Table.Body>
                    {#each extensions as ext}
                        <Table.Row>
                            <Table.Cell class="font-medium">
                                {ext.name}
                            </Table.Cell>
                            <Table.Cell>
                                {ext.description}
                            </Table.Cell>
                            <Table.Cell>
                                <div class="flex flex-wrap gap-1">
                                    {#each ext.granted_permissions as perm}
                                        <span class="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded-full">
                                            {perm}
                                        </span>
                                    {/each}
                                    
                                    {#if ext.granted_permissions.length === 0}
                                        <span class="text-gray-500 italic text-sm">None</span>
                                    {/if}
                                </div>
                            </Table.Cell>
                            <Table.Cell>
                                <div class="flex items-center">
                                    <Toggle 
                                        checked={ext.enabled} 
                                        on:change={() => toggleExtension(ext.name, ext.enabled)}
                                    />
                                    <span class="ml-2 text-sm {ext.enabled ? 'text-green-600' : 'text-gray-500'}">
                                        {ext.enabled ? 'Enabled' : 'Disabled'}
                                    </span>
                                </div>
                            </Table.Cell>
                            <Table.Cell>
                                <Button 
                                    size="xs" 
                                    color="alternative"
                                    on:click={() => openConfigModal(ext)}
                                >
                                    <CogSolid class="mr-1 h-4 w-4" />
                                    Configure
                                </Button>
                            </Table.Cell>
                        </Table.Row>
                    {/each}
                </Table.Body>
            </Table>
        {/if}
    </Card>
</div>

<!-- Configuration Modal -->
<Modal 
    bind:open={showConfigModal} 
    title={currentExtension ? `Configure ${currentExtension.name}` : 'Configure Extension'}
    size="lg"
>
    {#if currentExtension}
        <div class="mb-4">
            <p class="text-sm text-gray-600">
                Edit the extension configuration in JSON format.
            </p>
        </div>
        
        {#if configError}
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 text-sm">
                {configError}
            </div>
        {/if}
        
        <Textarea 
            rows="10" 
            bind:value={configJson}
            class="font-mono text-sm"
            disabled={configLoading}
        />
        
        <div class="flex justify-end space-x-2 mt-4">
            <Button color="alternative" on:click={() => showConfigModal = false} disabled={configLoading}>
                Cancel
            </Button>
            <Button color="primary" on:click={saveConfig} disabled={configLoading}>
                {#if configLoading}
                    <Spinner size="sm" class="mr-2" />
                {/if}
                Save Configuration
            </Button>
        </div>
    {/if}
</Modal>
