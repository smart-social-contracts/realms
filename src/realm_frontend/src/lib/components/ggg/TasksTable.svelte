<script>
  export let tasks = [];
  export let loading = false;
  
  function getTaskDescription(metadata) {
    if (!metadata) return 'N/A';
    try {
      const parsed = JSON.parse(metadata);
      return parsed.description || 'N/A';
    } catch (e) {
      return metadata || 'N/A';
    }
  }
</script>

<div class="w-full overflow-x-auto">
  <h2 class="text-xl font-bold mb-4 flex items-center">
    <span class="mr-2">📋</span>
    Tasks
  </h2>
  <p class="text-sm text-gray-600 mb-4">View and manage scheduled tasks</p>
  
  <div class="flex justify-between items-center mb-4">
    <div class="flex items-center">
      <span class="mr-2">Filter by status</span>
      <select class="border rounded px-2 py-1">
        <option value="all">All</option>
        <option value="pending">Pending</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
      </select>
    </div>
    <input type="text" placeholder="Search tasks..." class="border rounded px-3 py-1">
  </div>
  
  <table class="min-w-full bg-white">
    <thead>
      <tr class="bg-gray-100 border-b">
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">DESCRIPTION</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CODEX</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SCHEDULE</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ACTIONS</th>
      </tr>
    </thead>
    <tbody>
      {#if loading}
        <tr>
          <td colspan="5" class="px-6 py-4 text-center">Loading...</td>
        </tr>
      {:else if tasks.length === 0}
        <tr>
          <td colspan="5" class="px-6 py-4 text-center">No tasks found</td>
        </tr>
      {:else}
        {#each tasks as task}
          <tr class="border-b hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">{task._id || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{getTaskDescription(task.metadata)}</td>
            <td class="px-6 py-4 whitespace-nowrap">{task.codex?._id || 'None'}</td>
            <td class="px-6 py-4 whitespace-nowrap">
              {#if task.schedules && task.schedules.length > 0}
                {task.schedules[0].cron_expression || 'Not scheduled'}
              {:else}
                Not scheduled
              {/if}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-900 mr-2">View</button>
              <button class="text-green-600 hover:text-green-900 mr-2">Run</button>
              <button class="text-gray-600 hover:text-gray-900">Edit</button>
            </td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>
