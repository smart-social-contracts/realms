<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  
  import UsersTable from '$lib/components/ggg/UsersTable.svelte';
  import MandatesTable from '$lib/components/ggg/MandatesTable.svelte';
  import TasksTable from '$lib/components/ggg/TasksTable.svelte';
  import TransfersTable from '$lib/components/ggg/TransfersTable.svelte';
  
  let loading = true;
  let activeTab = 'users';
  let error = null;
  let data = {
    users: [],
    mandates: [],
    tasks: [],
    transfers: [],
    instruments: [],
    codexes: [],
    organizations: []
  };
  
  async function loadDemoData() {
    try {
      loading = true;
      error = null;
      
      console.log("Loading demo data...");
      const result = await backend.extension_sync_call({
        extension_name: "demo_loader",
        function_name: "load",
        args: "load_demo"
      });
      
      console.log("Demo data load result:", result);
      
      if (result.success) {
        console.log("Demo data loaded successfully:", result.response);
        await fetchData();
      } else {
        error = `Failed to load demo data: ${result.response || 'Unknown error'}`;
        console.error(error);
      }
    } catch (err) {
      error = `Error loading demo data: ${err.message}`;
      console.error("Demo data load error:", err);
    } finally {
      loading = false;
    }
  }
  
  async function fetchData() {
    try {
      loading = true;
      error = null;
      
      console.log("Fetching GGG data...");
      
      // Make API calls directly using the backend proxy
      console.log("Calling backend methods...");
      
      const [
        usersResult,
        mandatesResult,
        tasksResult,
        transfersResult
      ] = await Promise.all([
        backend.get_users(),
        backend.get_mandates(),
        backend.get_tasks(),
        backend.get_transfers()
      ]);
      
      console.log("API results received:", { 
        users: usersResult, 
        mandates: mandatesResult, 
        tasks: tasksResult, 
        transfers: transfersResult 
      });
      
      // Process users data
      if (usersResult.success && usersResult.data.UsersList) {
        data.users = usersResult.data.UsersList.users.map(userJson => JSON.parse(userJson));
        console.log("Users loaded:", data.users.length);
      } else if (!usersResult.success) {
        console.error("Failed to fetch users:", usersResult.data.Error);
      }
      
      // Process mandates data
      if (mandatesResult.success && mandatesResult.data.MandatesList) {
        data.mandates = mandatesResult.data.MandatesList.mandates.map(mandateJson => JSON.parse(mandateJson));
        console.log("Mandates loaded:", data.mandates.length);
      } else if (!mandatesResult.success) {
        console.error("Failed to fetch mandates:", mandatesResult.data.Error);
      }
      
      // Process tasks data
      if (tasksResult.success && tasksResult.data.TasksList) {
        data.tasks = tasksResult.data.TasksList.tasks.map(taskJson => JSON.parse(taskJson));
        console.log("Tasks loaded:", data.tasks.length);
      } else if (!tasksResult.success) {
        console.error("Failed to fetch tasks:", tasksResult.data.Error);
      }
      
      // Process transfers data
      if (transfersResult.success && transfersResult.data.TransfersList) {
        data.transfers = transfersResult.data.TransfersList.transfers.map(transferJson => JSON.parse(transferJson));
        console.log("Transfers loaded:", data.transfers.length);
      } else if (!transfersResult.success) {
        console.error("Failed to fetch transfers:", transfersResult.data.Error);
      }
      
    } catch (error) {
      console.error("Error fetching data:", error);
      error = `Data fetch error: ${error.message}`;
    } finally {
      loading = false;
    }
  }
  
  onMount(fetchData);
</script>

<div class="container mx-auto p-4">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-2xl font-bold">GGG Dashboard</h1>
    <button 
      class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded flex items-center"
      on:click={loadDemoData}
      disabled={loading}
    >
      {#if loading}
        <span class="mr-2">⏳</span> Loading...
      {:else}
        <span class="mr-2">🔄</span> Load Demo Data
      {/if}
    </button>
  </div>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4" role="alert">
      <p>{error}</p>
    </div>
  {/if}
  
  <div class="mb-6 border-b">
    <div class="flex">
      <button 
        class="px-4 py-2 {activeTab === 'users' ? 'border-b-2 border-blue-500 font-medium' : ''}"
        on:click={() => activeTab = 'users'}
      >
        Users
      </button>
      <button 
        class="px-4 py-2 {activeTab === 'mandates' ? 'border-b-2 border-blue-500 font-medium' : ''}"
        on:click={() => activeTab = 'mandates'}
      >
        Mandates
      </button>
      <button 
        class="px-4 py-2 {activeTab === 'tasks' ? 'border-b-2 border-blue-500 font-medium' : ''}"
        on:click={() => activeTab = 'tasks'}
      >
        Tasks
      </button>
      <button 
        class="px-4 py-2 {activeTab === 'transfers' ? 'border-b-2 border-blue-500 font-medium' : ''}"
        on:click={() => activeTab = 'transfers'}
      >
        Transfers
      </button>
    </div>
  </div>
  
  <div class="bg-white shadow rounded-lg p-6">
    {#if activeTab === 'users'}
      <UsersTable users={data.users} {loading} />
    {:else if activeTab === 'mandates'}
      <MandatesTable mandates={data.mandates} {loading} />
    {:else if activeTab === 'tasks'}
      <TasksTable tasks={data.tasks} {loading} />
    {:else if activeTab === 'transfers'}
      <TransfersTable transfers={data.transfers} {loading} />
    {/if}
  </div>
</div> 