from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.permission")


class Permission(Entity, TimestampedMixin):
    description = String(max_length=256)


"""
category,permission_id,description
Judicial Administration,create_dispute,File a dispute between parties
Judicial Administration,view_dispute,Access case files or metadata
Judicial Administration,accept_dispute,Accept dispute into jurisdiction
Judicial Administration,reject_dispute,Decline or dismiss a dispute
Judicial Administration,assign_dispute_to_admin,Delegate case to specific administrator
Judicial Administration,evaluate_evidence,Access and validate uploaded evidence
Judicial Administration,draft_resolution,Create but not yet finalize a resolution
Judicial Administration,issue_resolution,Finalize and publish a judicial resolution
Judicial Administration,link_resolution_to_contract,Bind a ruling to an existing contract
Judicial Administration,modify_ruling_terms,Edit the terms of a resolution (before finalization)
Judicial Administration,mark_resolution_as_final,Declare a resolution as enforceable
Judicial Administration,allow_appeal,Grant permission to escalate ruling
Judicial Administration,view_all_disputes_in_scope,List all disputes the admin can access

Judicial Execution,execute_trade,Carry out a resource transfer as part of enforcement
Judicial Execution,apply_fine,Deduct tokens from a party’s balance
Judicial Execution,revoke_access,Temporarily or permanently disable access to a service or area
Judicial Execution,terminate_contract,Cancel or deactivate a live contract
Judicial Execution,reassign_resource,Transfer ownership of land, NFTs, tokens, etc.
Judicial Execution,update_user_status,Mark user as "sanctioned", "inactive", etc.
Judicial Execution,lock_instrument,Freeze the usage of a specific instrument
Judicial Execution,send_notification,Inform affected parties of enforcement action
Judicial Execution,query_resolution,Check if a resolution applies to the executor’s domain
Judicial Execution,escalate_to_supervisor,Push a case up the enforcement chain
Judicial Execution,record_enforcement_action,Log action for audit trail

General Governance,create_mandate,Define a new public purpose or policy rule
General Governance,assign_executor_to_mandate,Designate who enforces a mandate
General Governance,authorize_party_for_scope,Give someone authority over a domain (e.g., land, health)
General Governance,view_party_permissions,Check what another party is allowed to do
General Governance,revoke_permission,Remove any previously granted ability
General Governance,update_governance_process,Change voting or approval mechanics
General Governance,create_contract_under_mandate,Bind new contracts to policy-based logic
"""
