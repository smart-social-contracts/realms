import TaskMonitor from './TaskMonitor.svelte';

export const metadata = {
  "name": "task_monitor",
  "version": "1.0.0",
  "description": "Task monitoring and management dashboard for administrators",
  "author": "Realms Team",
  "categories": [
    "other"
  ],
  "permissions": [
    "admin"
  ],
  "profiles": [
    "admin"
  ],
  "url_path": "tasks",
  "show_in_sidebar": true
};

export default TaskMonitor;
