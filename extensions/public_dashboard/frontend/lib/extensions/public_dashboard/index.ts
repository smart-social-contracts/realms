import { default as PublicDashboard } from './PublicDashboard.svelte';

export default PublicDashboard;

export const metadata = {
  name: "Public Dashboard",
  description: "View platform statistics including users, organizations, and assets with interactive charts",
  icon: "chart-pie",
  author: "Smart Social Contracts",
  permissions: ["read"],
  version: "1.0.0"
};
