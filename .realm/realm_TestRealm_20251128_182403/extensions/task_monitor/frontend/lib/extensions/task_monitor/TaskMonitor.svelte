<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { backend } from '$lib/canisters';
  import { Button, Badge, Card, Modal, Spinner, Table, TableHead, TableHeadCell, TableBody, TableBodyCell, TableBodyRow } from 'flowbite-svelte';
  
  interface TaskSchedule {
    _id: string;
    name: string;
    disabled: boolean;
    run_at: number;
    repeat_every: number;
    last_run_at: number;
  }
  
  interface Task {
    _id: string;
    name: string;
    status: string;
    metadata: string;
    step_to_execute: number;
    total_steps: number;
    schedules: TaskSchedule[];
    executions_count: number;
    created_at: number | null;
    updated_at: number | null;
  }
  
  interface TaskExecution {
    _id: string;
    name: string;
    status: string;
    logs: string;
    result: string;
    created_at: number | null;
    updated_at: number | null;
  }
  
  let tasks: Task[] = [];
  let loading = true;
  let error = '';
  let selectedTask: any = null;
  let showDetailModal = false;
  let showExecutionsModal = false;
  let taskExecutions: TaskExecution[] = [];
  let refreshInterval: any = null;
  
  onMount(() => {
    loadTasks();
    // Auto-refresh every 10 seconds
    refreshInterval = setInterval(loadTasks, 10000);
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });
  
  async function loadTasks() {
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'get_all_tasks',
        args: '{}'
      });
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        tasks = data.tasks || [];
        error = '';
      } else {
        error = response.response || 'Failed to load tasks';
      }
    } catch (e) {
      error = 'Error loading tasks: ' + e.message;
    } finally {
      loading = false;
    }
  }
  
  async function viewTaskDetails(taskId: string) {
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'get_task_details',
        args: JSON.stringify({ task_id: taskId })
      });
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        selectedTask = data.task;
        showDetailModal = true;
      } else {
        alert(response.error || 'Failed to load task details');
      }
    } catch (e: any) {
      alert(e.message || 'Error loading task details');
    }
  }
  
  async function viewExecutions(taskId: string) {
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'get_task_executions',
        args: JSON.stringify({ task_id: taskId, limit: 50 })
      });
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        taskExecutions = data.executions || [];
        showExecutionsModal = true;
      } else {
        alert(response.error || 'Failed to load executions');
      }
    } catch (e: any) {
      alert(e.message || 'Error loading executions');
    }
  }
  
  async function toggleSchedule(scheduleId: string, disabled: boolean) {
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'toggle_schedule',
        args: JSON.stringify({ 
          schedule_id: scheduleId, 
          disabled: !disabled 
        })
      });
      if (response.success) {
        await loadTasks();
      } else {
        alert(response.error || 'Failed to toggle schedule');
      }
    } catch (e: any) {
      alert(e.message || 'Error toggling schedule');
    }
  }
  
  async function runTaskNow(taskId: string) {
    if (!confirm($_('extensions.task_monitor.confirm_run'))) return;
    
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'run_task_now',
        args: JSON.stringify({ task_id: taskId })
      });
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        alert(data.message || 'Task started');
        await loadTasks();
      } else {
        alert(response.error || 'Failed to run task');
      }
    } catch (e: any) {
      alert(e.message || 'Error running task');
    }
  }
  
  async function deleteTask(taskId: string) {
    if (!confirm($_('extensions.task_monitor.confirm_delete'))) return;
    
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'delete_task',
        args: JSON.stringify({ task_id: taskId })
      });
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        alert(data.message || 'Task deleted');
        await loadTasks();
      } else {
        alert(response.error || 'Failed to delete task');
      }
    } catch (e: any) {
      alert(e.message || 'Error deleting task');
    }
  }
  
  function getStatusBadge(status: string) {
    const statusMap: Record<string, string> = {
      'pending': 'yellow',
      'running': 'blue',
      'completed': 'green',
      'failed': 'red',
      'cancelled': 'gray'
    };
    return statusMap[status.toLowerCase()] || 'gray';
  }
  
  function formatTimestamp(timestamp: number | null): string {
    if (!timestamp) return '-';
    return new Date(timestamp / 1000000).toLocaleString();
  }
  
  function formatInterval(seconds: number): string {
    if (!seconds) return 'One-time';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `Every ${hours}h ${minutes}m`;
    if (minutes > 0) return `Every ${minutes}m`;
    return `Every ${seconds}s`;
  }
</script>

<div class="p-6">
  <div class="mb-6 flex justify-between items-center">
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
      {$_('extensions.task_monitor.title')}
    </h1>
    <Button on:click={loadTasks} size="sm">
      {$_('extensions.task_monitor.refresh')}
    </Button>
  </div>

  {#if error}
    <div class="mb-4 p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center items-center py-12">
      <Spinner size="12" />
    </div>
  {:else if tasks.length === 0}
    <Card>
      <p class="text-gray-500 dark:text-gray-400 text-center py-8">
        {$_('extensions.task_monitor.no_tasks')}
      </p>
    </Card>
  {:else}
    <div class="overflow-x-auto">
      <Table striped={true}>
        <TableHead>
          <TableHeadCell>{$_('extensions.task_monitor.name')}</TableHeadCell>
          <TableHeadCell>{$_('extensions.task_monitor.status')}</TableHeadCell>
          <TableHeadCell>{$_('extensions.task_monitor.progress')}</TableHeadCell>
          <TableHeadCell>{$_('extensions.task_monitor.schedule')}</TableHeadCell>
          <TableHeadCell>{$_('extensions.task_monitor.executions')}</TableHeadCell>
          <TableHeadCell>{$_('extensions.task_monitor.actions')}</TableHeadCell>
        </TableHead>
        <TableBody>
          {#each tasks as task}
            <TableBodyRow>
              <TableBodyCell>
                <div>
                  <div class="font-medium text-gray-900 dark:text-white">{task.name}</div>
                  {#if task.metadata}
                    <div class="text-sm text-gray-500 dark:text-gray-400">{task.metadata}</div>
                  {/if}
                  <div class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    ID: {task._id.substring(0, 8)}...
                  </div>
                </div>
              </TableBodyCell>
              <TableBodyCell>
                <Badge color={getStatusBadge(task.status)}>
                  {task.status}
                </Badge>
              </TableBodyCell>
              <TableBodyCell>
                <div class="text-sm">
                  {task.step_to_execute} / {task.total_steps} steps
                </div>
                {#if task.total_steps > 0}
                  <div class="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700 mt-1">
                    <div class="bg-blue-600 h-2 rounded-full" style="width: {(task.step_to_execute / task.total_steps) * 100}%"></div>
                  </div>
                {/if}
              </TableBodyCell>
              <TableBodyCell>
                {#if task.schedules.length > 0}
                  {#each task.schedules as schedule}
                    <div class="mb-1">
                      <Badge color={schedule.disabled ? 'gray' : 'green'}>
                        {formatInterval(schedule.repeat_every)}
                      </Badge>
                      <button
                        on:click={() => toggleSchedule(schedule._id, schedule.disabled)}
                        class="ml-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        {schedule.disabled ? 'Enable' : 'Disable'}
                      </button>
                    </div>
                  {/each}
                {:else}
                  <span class="text-gray-500 dark:text-gray-400">-</span>
                {/if}
              </TableBodyCell>
              <TableBodyCell>
                <button
                  on:click={() => viewExecutions(task._id)}
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {task.executions_count}
                </button>
              </TableBodyCell>
              <TableBodyCell>
                <div class="flex gap-2">
                  <Button size="xs" color="light" on:click={() => viewTaskDetails(task._id)}>
                    {$_('extensions.task_monitor.view')}
                  </Button>
                  <Button size="xs" color="blue" on:click={() => runTaskNow(task._id)}>
                    {$_('extensions.task_monitor.run')}
                  </Button>
                  <Button size="xs" color="red" on:click={() => deleteTask(task._id)}>
                    {$_('extensions.task_monitor.delete')}
                  </Button>
                </div>
              </TableBodyCell>
            </TableBodyRow>
          {/each}
        </TableBody>
      </Table>
    </div>
  {/if}
</div>

<!-- Task Details Modal -->
<Modal bind:open={showDetailModal} size="xl" autoclose={false}>
  <div slot="header">
    <h3 class="text-xl font-semibold">{$_('extensions.task_monitor.task_details')}</h3>
  </div>
  
  {#if selectedTask}
    <div class="space-y-4">
      <div>
        <h4 class="font-semibold mb-2">{$_('extensions.task_monitor.basic_info')}</h4>
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div><strong>Name:</strong> {selectedTask.name}</div>
          <div><strong>Status:</strong> <Badge color={getStatusBadge(selectedTask.status)}>{selectedTask.status}</Badge></div>
          <div><strong>ID:</strong> {selectedTask._id}</div>
          <div><strong>Progress:</strong> {selectedTask.step_to_execute} / {selectedTask.steps?.length || 0} steps</div>
        </div>
      </div>
      
      {#if selectedTask.steps && selectedTask.steps.length > 0}
        <div>
          <h4 class="font-semibold mb-2">{$_('extensions.task_monitor.steps')}</h4>
          {#each selectedTask.steps as step, i}
            <Card class="mb-2">
              <div class="flex justify-between items-start">
                <div>
                  <div class="font-medium">Step {i + 1}</div>
                  <Badge color={getStatusBadge(step.status)} class="mt-1">{step.status}</Badge>
                  {#if step.is_async}
                    <Badge color="purple" class="mt-1 ml-2">Async</Badge>
                  {/if}
                </div>
              </div>
              {#if step.codex}
                <div class="mt-2">
                  <div class="text-sm font-medium">{$_('extensions.task_monitor.codex')}: {step.codex.name}</div>
                  {#if step.codex.description}
                    <div class="text-sm text-gray-600 dark:text-gray-400">{step.codex.description}</div>
                  {/if}
                  <details class="mt-2">
                    <summary class="cursor-pointer text-sm text-blue-600 dark:text-blue-400">
                      {$_('extensions.task_monitor.show_code')}
                    </summary>
                    <pre class="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-x-auto">{step.codex.code}</pre>
                  </details>
                </div>
              {/if}
            </Card>
          {/each}
        </div>
      {/if}
      
      {#if selectedTask.schedules && selectedTask.schedules.length > 0}
        <div>
          <h4 class="font-semibold mb-2">{$_('extensions.task_monitor.schedules')}</h4>
          {#each selectedTask.schedules as schedule}
            <Card class="mb-2">
              <div class="grid grid-cols-2 gap-2 text-sm">
                <div><strong>Name:</strong> {schedule.name}</div>
                <div><strong>Interval:</strong> {formatInterval(schedule.repeat_every)}</div>
                <div><strong>Status:</strong> 
                  <Badge color={schedule.disabled ? 'gray' : 'green'}>
                    {schedule.disabled ? 'Disabled' : 'Enabled'}
                  </Badge>
                </div>
                <div><strong>Last Run:</strong> {formatTimestamp(schedule.last_run_at)}</div>
              </div>
            </Card>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</Modal>

<!-- Executions Modal -->
<Modal bind:open={showExecutionsModal} size="xl" autoclose={false}>
  <div slot="header">
    <h3 class="text-xl font-semibold">{$_('extensions.task_monitor.execution_history')}</h3>
  </div>
  
  {#if taskExecutions.length === 0}
    <p class="text-gray-500 dark:text-gray-400 text-center py-8">
      {$_('extensions.task_monitor.no_executions')}
    </p>
  {:else}
    <div class="space-y-2 max-h-96 overflow-y-auto">
      {#each taskExecutions as execution}
        <Card>
          <div class="flex justify-between items-start mb-2">
            <div>
              <div class="font-medium">{execution.name}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">
                {formatTimestamp(execution.created_at)}
              </div>
            </div>
            <Badge color={getStatusBadge(execution.status)}>{execution.status}</Badge>
          </div>
          {#if execution.result}
            <div class="mt-2 text-sm">
              <strong>{$_('extensions.task_monitor.result')}:</strong>
              <pre class="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-x-auto">{execution.result}</pre>
            </div>
          {/if}
          {#if execution.logs}
            <details class="mt-2">
              <summary class="cursor-pointer text-sm text-blue-600 dark:text-blue-400">
                {$_('extensions.task_monitor.show_logs')}
              </summary>
              <pre class="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-x-auto">{execution.logs}</pre>
            </details>
          {/if}
        </Card>
      {/each}
    </div>
  {/if}
</Modal>

<style>
  :global(.dark) pre {
    color: #e5e7eb;
  }
</style>
