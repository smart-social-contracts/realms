import { default as CitizenDashboard } from './CitizenDashboard.svelte';
import { default as ServicesList } from './ServicesList.svelte';
import { default as TaxInformation } from './TaxInformation.svelte';
import { default as PersonalData } from './PersonalData.svelte';
import { UserCircleOutline } from 'flowbite-svelte-icons';

export default CitizenDashboard;

export const metadata = {
  name: "Citizen Dashboard",
  description: "View your public services, tax information, and personal data in one place",
  icon: UserCircleOutline,
  author: "Smart Social Contracts",
  permissions: ["read"],
  subComponents: {
    ServicesList,
    TaxInformation,
    PersonalData
  }
};
