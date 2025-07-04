<script lang="ts">
  // Pure UI/UX development route - no backend dependencies
  import { onMount } from 'svelte';
  import { Button, Card, Badge, Avatar, Dropdown, DropdownItem } from 'flowbite-svelte';
  import { ChevronDownOutline, UserCircleOutline, CogOutline, SignOutOutline } from 'flowbite-svelte-icons';
  
  // Mock data for UI development
  let mockUser = {
    name: "Demo User",
    email: "demo@example.com",
    avatar: "/images/avatar.jpg",
    role: "Member"
  };
  
  let mockStats = {
    users: 42,
    organizations: 8,
    proposals: 15,
    votes: 127
  };
  
  let mockNotifications = [
    { id: 1, title: "New Proposal", message: "A new governance proposal has been submitted", time: "2 hours ago", unread: true },
    { id: 2, title: "Vote Reminder", message: "Don't forget to vote on Proposal #15", time: "1 day ago", unread: false },
    { id: 3, title: "Organization Update", message: "Demo Organization has been updated", time: "3 days ago", unread: false }
  ];
  
  let currentView = 'dashboard';
  
  function switchView(view: string) {
    currentView = view;
    console.log('Switched to view:', view);
  }
  
  onMount(() => {
    console.log('=== DEV UI MODE LOADED ===');
    console.log('This is a pure UI/UX development environment');
    console.log('No backend dependencies - perfect for hot reloading!');
  });
</script>

<svelte:head>
  <title>Realms - Dev UI Mode</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
  <!-- Header -->
  <header class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
    <div class="px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center py-4">
        <!-- Logo -->
        <div class="flex items-center">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Realms <Badge color="green" class="ml-2">DEV UI</Badge>
          </h1>
        </div>
        
        <!-- User Menu -->
        <div class="flex items-center space-x-4">
          <!-- Notifications -->
          <Button color="light" class="relative">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
            </svg>
            <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
              {mockNotifications.filter(n => n.unread).length}
            </span>
          </Button>
          
          <!-- User Dropdown -->
          <Dropdown>
            <Button color="light" slot="trigger" class="flex items-center space-x-2">
              <Avatar src={mockUser.avatar} alt={mockUser.name} size="sm" />
              <span class="hidden md:block">{mockUser.name}</span>
              <ChevronDownOutline class="w-4 h-4" />
            </Button>
            <DropdownItem>
              <UserCircleOutline class="w-4 h-4 mr-2" />
              Profile
            </DropdownItem>
            <DropdownItem>
              <CogOutline class="w-4 h-4 mr-2" />
              Settings
            </DropdownItem>
            <DropdownItem>
              <SignOutOutline class="w-4 h-4 mr-2" />
              Sign Out
            </DropdownItem>
          </Dropdown>
        </div>
      </div>
    </div>
  </header>

  <div class="flex">
    <!-- Sidebar -->
    <aside class="w-64 bg-white dark:bg-gray-800 shadow-sm min-h-screen">
      <nav class="p-4 space-y-2">
        <Button 
          color={currentView === 'dashboard' ? 'primary' : 'light'} 
          class="w-full justify-start"
          on:click={() => switchView('dashboard')}
        >
          Dashboard
        </Button>
        <Button 
          color={currentView === 'users' ? 'primary' : 'light'} 
          class="w-full justify-start"
          on:click={() => switchView('users')}
        >
          Users
        </Button>
        <Button 
          color={currentView === 'organizations' ? 'primary' : 'light'} 
          class="w-full justify-start"
          on:click={() => switchView('organizations')}
        >
          Organizations
        </Button>
        <Button 
          color={currentView === 'proposals' ? 'primary' : 'light'} 
          class="w-full justify-start"
          on:click={() => switchView('proposals')}
        >
          Proposals
        </Button>
        <Button 
          color={currentView === 'settings' ? 'primary' : 'light'} 
          class="w-full justify-start"
          on:click={() => switchView('settings')}
        >
          Settings
        </Button>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 p-6">
      {#if currentView === 'dashboard'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h2>
          
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card class="text-center">
              <h3 class="text-2xl font-bold text-blue-600">{mockStats.users}</h3>
              <p class="text-gray-600 dark:text-gray-400">Total Users</p>
            </Card>
            <Card class="text-center">
              <h3 class="text-2xl font-bold text-green-600">{mockStats.organizations}</h3>
              <p class="text-gray-600 dark:text-gray-400">Organizations</p>
            </Card>
            <Card class="text-center">
              <h3 class="text-2xl font-bold text-purple-600">{mockStats.proposals}</h3>
              <p class="text-gray-600 dark:text-gray-400">Active Proposals</p>
            </Card>
            <Card class="text-center">
              <h3 class="text-2xl font-bold text-orange-600">{mockStats.votes}</h3>
              <p class="text-gray-600 dark:text-gray-400">Total Votes</p>
            </Card>
          </div>
          
          <!-- Recent Activity -->
          <Card>
            <h3 class="text-xl font-semibold mb-4">Recent Notifications</h3>
            <div class="space-y-3">
              {#each mockNotifications as notification}
                <div class="flex items-start space-x-3 p-3 rounded-lg {notification.unread ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-gray-700'}">
                  <div class="flex-1">
                    <h4 class="font-medium text-gray-900 dark:text-white">{notification.title}</h4>
                    <p class="text-sm text-gray-600 dark:text-gray-400">{notification.message}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-500 mt-1">{notification.time}</p>
                  </div>
                  {#if notification.unread}
                    <Badge color="blue" class="text-xs">New</Badge>
                  {/if}
                </div>
              {/each}
            </div>
          </Card>
        </div>
      {:else if currentView === 'users'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900 dark:text-white">Users</h2>
          <Card>
            <p class="text-gray-600 dark:text-gray-400">User management interface would go here.</p>
            <p class="text-sm text-gray-500 dark:text-gray-500 mt-2">This is a UI development environment - modify this component to test your designs!</p>
          </Card>
        </div>
      {:else if currentView === 'organizations'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900 dark:text-white">Organizations</h2>
          <Card>
            <p class="text-gray-600 dark:text-gray-400">Organization management interface would go here.</p>
            <p class="text-sm text-gray-500 dark:text-gray-500 mt-2">Perfect for testing organization-related UI components!</p>
          </Card>
        </div>
      {:else if currentView === 'proposals'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900 dark:text-white">Proposals</h2>
          <Card>
            <p class="text-gray-600 dark:text-gray-400">Proposal management interface would go here.</p>
            <p class="text-sm text-gray-500 dark:text-gray-500 mt-2">Test your governance UI designs here!</p>
          </Card>
        </div>
      {:else if currentView === 'settings'}
        <div class="space-y-6">
          <h2 class="text-3xl font-bold text-gray-900 dark:text-white">Settings</h2>
          <Card>
            <p class="text-gray-600 dark:text-gray-400">Settings interface would go here.</p>
            <p class="text-sm text-gray-500 dark:text-gray-500 mt-2">Configure your UI preferences and test settings components!</p>
          </Card>
        </div>
      {/if}
    </main>
  </div>
</div>

<style>
  /* Custom styles for dev UI mode */
  :global(body) {
    font-family: 'Inter', sans-serif;
  }
</style>
