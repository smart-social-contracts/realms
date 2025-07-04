<script>
  // Completely standalone UI development environment
  // No backend dependencies, no canisters, no complex imports
  import { onMount } from 'svelte';
  
  let currentView = 'dashboard';
  let notifications = [
    { id: 1, title: "New Proposal", message: "A new governance proposal has been submitted", unread: true },
    { id: 2, title: "Vote Reminder", message: "Don't forget to vote on Proposal #15", unread: false },
    { id: 3, title: "Organization Update", message: "Demo Organization has been updated", unread: false }
  ];
  
  let stats = {
    users: 42,
    organizations: 8,
    proposals: 15,
    votes: 127
  };
  
  function switchView(view) {
    currentView = view;
    console.log('Switched to view:', view);
  }
  
  onMount(() => {
    console.log('=== STANDALONE DEV UI LOADED ===');
    console.log('Pure UI/UX development environment - no backend dependencies!');
    console.log('Perfect for hot reloading and frontend design work!');
  });
</script>

<svelte:head>
  <title>Realms - Standalone Dev UI</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <header class="bg-white shadow-sm border-b border-gray-200">
    <div class="px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center py-4">
        <!-- Logo -->
        <div class="flex items-center">
          <h1 class="text-2xl font-bold text-gray-900">
            Realms 
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 ml-2">
              STANDALONE DEV
            </span>
          </h1>
        </div>
        
        <!-- User Menu -->
        <div class="flex items-center space-x-4">
          <!-- Notifications -->
          <button class="relative p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5v-5zM10.586 3l-6.586 6.586a2 2 0 000 2.828l6.586 6.586a2 2 0 002.828 0l6.586-6.586a2 2 0 000-2.828L13.414 3a2 2 0 00-2.828 0z"/>
            </svg>
            <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
              {notifications.filter(n => n.unread).length}
            </span>
          </button>
          
          <!-- User Avatar -->
          <div class="flex items-center space-x-2">
            <div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <span class="text-white text-sm font-medium">DU</span>
            </div>
            <span class="text-sm font-medium text-gray-700">Demo User</span>
          </div>
        </div>
      </div>
    </div>
  </header>

  <div class="flex">
    <!-- Sidebar -->
    <aside class="w-64 bg-white shadow-sm min-h-screen">
      <nav class="p-4 space-y-2">
        <button 
          class="w-full text-left px-4 py-2 rounded-lg transition-colors {currentView === 'dashboard' ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}"
          on:click={() => switchView('dashboard')}
        >
          📊 Dashboard
        </button>
        <button 
          class="w-full text-left px-4 py-2 rounded-lg transition-colors {currentView === 'users' ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}"
          on:click={() => switchView('users')}
        >
          👥 Users
        </button>
        <button 
          class="w-full text-left px-4 py-2 rounded-lg transition-colors {currentView === 'organizations' ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}"
          on:click={() => switchView('organizations')}
        >
          🏢 Organizations
        </button>
        <button 
          class="w-full text-left px-4 py-2 rounded-lg transition-colors {currentView === 'proposals' ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}"
          on:click={() => switchView('proposals')}
        >
          📋 Proposals
        </button>
        <button 
          class="w-full text-left px-4 py-2 rounded-lg transition-colors {currentView === 'settings' ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}"
          on:click={() => switchView('settings')}
        >
          ⚙️ Settings
        </button>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 p-6">
      {#if currentView === 'dashboard'}
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <h2 class="text-3xl font-bold text-gray-900">Dashboard</h2>
            <div class="text-sm text-green-600 font-medium animate-pulse">
              🚀 Hot Reloading WORKING - Changes appear instantly! 🎨
            </div>
          </div>
          
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div class="text-center">
                <div class="text-3xl font-bold text-blue-600">{stats.users}</div>
                <div class="text-gray-600 mt-1">Total Users</div>
              </div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div class="text-center">
                <div class="text-3xl font-bold text-green-600">{stats.organizations}</div>
                <div class="text-gray-600 mt-1">Organizations</div>
              </div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div class="text-center">
                <div class="text-3xl font-bold text-purple-600">{stats.proposals}</div>
                <div class="text-gray-600 mt-1">Active Proposals</div>
              </div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div class="text-center">
                <div class="text-3xl font-bold text-orange-600">{stats.votes}</div>
                <div class="text-gray-600 mt-1">Total Votes</div>
              </div>
            </div>
          </div>
          
          <!-- Recent Activity -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200">
            <div class="p-6">
              <h3 class="text-xl font-semibold mb-4">Recent Notifications</h3>
              <div class="space-y-3">
                {#each notifications as notification}
                  <div class="flex items-start space-x-3 p-4 rounded-lg {notification.unread ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'}">
                    <div class="flex-1">
                      <h4 class="font-medium text-gray-900">{notification.title}</h4>
                      <p class="text-sm text-gray-600 mt-1">{notification.message}</p>
                    </div>
                    {#if notification.unread}
                      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        New
                      </span>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      {:else if currentView === 'users'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900">Users</h2>
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p class="text-gray-600">User management interface would go here.</p>
            <p class="text-sm text-gray-500 mt-2">
              🎨 This is your UI development playground! 
              <br>Modify this component to test your user interface designs.
              <br>Changes will appear instantly thanks to hot reloading!
            </p>
          </div>
        </div>
      {:else if currentView === 'organizations'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900">Organizations</h2>
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p class="text-gray-600">Organization management interface would go here.</p>
            <p class="text-sm text-gray-500 mt-2">
              🏢 Perfect for testing organization-related UI components!
              <br>Add tables, forms, modals, or any other UI elements you need.
            </p>
          </div>
        </div>
      {:else if currentView === 'proposals'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900">Proposals</h2>
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p class="text-gray-600">Proposal management interface would go here.</p>
            <p class="text-sm text-gray-500 mt-2">
              📋 Test your governance UI designs here!
              <br>Create voting interfaces, proposal cards, status indicators, etc.
            </p>
          </div>
        </div>
      {:else if currentView === 'settings'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900">Settings</h2>
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p class="text-gray-600">Settings interface would go here.</p>
            <p class="text-sm text-gray-500 mt-2">
              ⚙️ Configure your UI preferences and test settings components!
              <br>Try different themes, layouts, or configuration options.
            </p>
          </div>
        </div>
      {/if}
    </main>
  </div>
</div>

<style>
  /* Additional custom styles can go here */
  button {
    transition: all 0.2s ease-in-out;
  }
  
  button:hover {
    transform: translateY(-1px);
  }
</style>
