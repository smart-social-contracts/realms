import { default as Voting } from './Voting.svelte';
import { default as ProposalList } from './ProposalList.svelte';
import { default as ProposalForm } from './ProposalForm.svelte';
import { default as ProposalDetail } from './ProposalDetail.svelte';
import { default as VotingCard } from './VotingCard.svelte';

export default Voting;

export const metadata = {
  name: "Voting",
  version: "1.0.0",
  description: "Governance voting system for submitting and voting on proposals to execute Python code",
  author: "Smart Social Contracts",
  permissions: [],
  profiles: ["member", "admin"],
  categories: ["public_services"],
  icon: "vote",
  doc_url: "https://github.com/smart-social-contracts/realms/tree/main/extensions/voting",
  url_path: null,
  show_in_sidebar: true
};

export {
  ProposalList,
  ProposalForm,
  ProposalDetail,
  VotingCard
};
