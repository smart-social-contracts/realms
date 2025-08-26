<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { Button, Card, Select, Textarea, Alert, Spinner } from 'flowbite-svelte';
  import { backend } from '$lib/canisters';

  let selectedEntityType = 'users';
  let dataFormat = 'csv';
  let dataContent = '';
  let isLoading = false;
  let result = '';
  let error = '';
  let templates: any = {};

  const entityTypes = [
    { value: 'users', name: 'Users' },
    { value: 'humans', name: 'Humans' },
    { value: 'organizations', name: 'Organizations' },
    { value: 'mandates', name: 'Mandates' },
    { value: 'codexes', name: 'Codexes' },
    { value: 'instruments', name: 'Instruments' }
  ];

  const formats = [
    { value: 'csv', name: 'CSV' },
    { value: 'json', name: 'JSON' }
  ];

  onMount(async () => {
    await loadTemplates();
  });

  async function loadTemplates() {
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'bulk_importer',
        function_name: 'get_templates',
        args: '{}'
      });
      templates = JSON.parse(response);
    } catch (e) {
      console.error('Error loading templates:', e);
    }
  }

  async function importData() {
    if (!dataContent.trim()) {
      error = 'Please provide data to import';
      return;
    }

    isLoading = true;
    error = '';
    result = '';

    try {
      const args = JSON.stringify({
        entity_type: selectedEntityType,
        data: dataContent,
        format: dataFormat,
        batch_size: 50
      });

      const response = await backend.extension_sync_call({
        extension_name: 'bulk_importer',
        function_name: 'import_data',
        args: args
      });
      result = response;
    } catch (e) {
      error = `Import failed: ${e}`;
    } finally {
      isLoading = false;
    }
  }

  function loadTemplate() {
    const template = templates[selectedEntityType];
    if (template && dataFormat === 'csv') {
      // Generate CSV template
      const headers = template.headers.join(',');
      const examples = template.example.map(row => row.join(',')).join('\n');
      dataContent = `${headers}\n${examples}`;
    } else if (template && dataFormat === 'json') {
      // Generate JSON template
      const jsonTemplate = template.example.map(row => {
        const obj: any = {};
        template.headers.forEach((header: string, index: number) => {
          obj[header] = row[index] || '';
        });
        return obj;
      });
      dataContent = JSON.stringify(jsonTemplate, null, 2);
    }
  }

  function clearData() {
    dataContent = '';
    result = '';
    error = '';
  }
</script>

<div class="p-6 max-w-4xl mx-auto">
  <h1 class="text-3xl font-bold mb-6">Bulk Data Importer</h1>
  
  <Card class="mb-6">
    <div class="space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-2">Entity Type</label>
          <Select bind:value={selectedEntityType} items={entityTypes} />
        </div>
        
        <div>
          <label class="block text-sm font-medium mb-2">Data Format</label>
          <Select bind:value={dataFormat} items={formats} />
        </div>
      </div>

      <div class="flex gap-2">
        <Button on:click={loadTemplate} color="light">
          Load Template
        </Button>
        <Button on:click={clearData} color="light">
          Clear
        </Button>
      </div>

      <div>
        <label class="block text-sm font-medium mb-2">
          Data ({dataFormat.toUpperCase()})
        </label>
        <Textarea 
          bind:value={dataContent}
          rows="12"
          placeholder={`Paste your ${dataFormat.toUpperCase()} data here or click "Load Template" to see an example`}
          class="font-mono text-sm"
        />
      </div>

      <Button 
        on:click={importData} 
        disabled={isLoading || !dataContent.trim()}
        class="w-full"
      >
        {#if isLoading}
          <Spinner class="mr-2" size="4" />
          Importing...
        {:else}
          Import Data
        {/if}
      </Button>
    </div>
  </Card>

  {#if error}
    <Alert color="red" class="mb-4">
      <span class="font-medium">Error:</span> {error}
    </Alert>
  {/if}

  {#if result}
    <Alert color="green" class="mb-4">
      <span class="font-medium">Success:</span> {result}
    </Alert>
  {/if}

  <Card>
    <h3 class="text-lg font-semibold mb-3">Instructions</h3>
    <div class="text-sm text-gray-600 space-y-2">
      <p><strong>CSV Format:</strong> First row should contain headers, followed by data rows.</p>
      <p><strong>JSON Format:</strong> Array of objects or single object with the required fields.</p>
      <p><strong>Batch Size:</strong> Data is processed in batches of 50 items to avoid system limits.</p>
      <p><strong>Templates:</strong> Click "Load Template" to see example data for each entity type.</p>
    </div>
  </Card>
</div>
