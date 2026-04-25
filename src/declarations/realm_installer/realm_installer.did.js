export const idlFactory = ({ IDL }) => {
  const AllocateOk = IDL.Record({
    'backend_canister_id' : IDL.Text,
    'already_allocated' : IDL.Bool,
    'job_id' : IDL.Text,
    'frontend_canister_id' : IDL.Text,
  });
  const InstallerError = IDL.Record({
    'message' : IDL.Text,
    'traceback' : IDL.Text,
  });
  const ResultAllocate = IDL.Variant({
    'Ok' : AllocateOk,
    'Err' : InstallerError,
  });
  const JobStatusAck = IDL.Record({
    'status' : IDL.Text,
    'prev_status' : IDL.Text,
    'noop' : IDL.Bool,
    'job_id' : IDL.Text,
  });
  const ResultJobCancel = IDL.Variant({
    'Ok' : JobStatusAck,
    'Err' : InstallerError,
  });
  const DebugResumeItem = IDL.Record({
    'status' : IDL.Text,
    'task_id' : IDL.Text,
    'pending_steps' : IDL.Nat32,
    'note' : IDL.Text,
    'reset_running' : IDL.Nat32,
    'target' : IDL.Text,
  });
  const DebugResumeOk = IDL.Record({ 'entries' : IDL.Vec(DebugResumeItem) });
  const ResultDebugResume = IDL.Variant({
    'Ok' : DebugResumeOk,
    'Err' : InstallerError,
  });
  const DebugRunStepOk = IDL.Record({
    'step_label' : IDL.Text,
    'step_error' : IDL.Text,
    'task_status' : IDL.Text,
    'message' : IDL.Text,
    'step_idx' : IDL.Nat32,
    'remaining_pending' : IDL.Nat32,
    'step_status' : IDL.Text,
    'step_kind' : IDL.Text,
  });
  const ResultDebugRunStep = IDL.Variant({
    'Ok' : DebugRunStepOk,
    'Err' : InstallerError,
  });
  const DeployFrontendOk = IDL.Record({
    'gzip_variants' : IDL.Nat32,
    'files_deployed' : IDL.Nat32,
    'operations_count' : IDL.Nat32,
    'frontend_namespace' : IDL.Text,
    'target_canister_id' : IDL.Text,
  });
  const ResultDeployFrontend = IDL.Variant({
    'Ok' : DeployFrontendOk,
    'Err' : InstallerError,
  });
  const EnqueueOk = IDL.Record({
    'status' : IDL.Text,
    'network' : IDL.Text,
    'job_id' : IDL.Text,
    'realm_name' : IDL.Text,
  });
  const ResultEnqueue = IDL.Variant({
    'Ok' : EnqueueOk,
    'Err' : InstallerError,
  });
  const FetchModuleHashOk = IDL.Record({
    'wasm_module_hash_hex' : IDL.Text,
    'wasm_namespace' : IDL.Text,
    'wasm_path' : IDL.Text,
    'wasm_size' : IDL.Nat64,
  });
  const ResultFetchModuleHash = IDL.Variant({
    'Ok' : FetchModuleHashOk,
    'Err' : InstallerError,
  });
  const DeploymentJobView = IDL.Record({
    'status' : IDL.Text,
    'expected_wasm_hash' : IDL.Text,
    'registry_canister_id' : IDL.Text,
    'backend_canister_id' : IDL.Text,
    'offchain_deployer_principal' : IDL.Text,
    'ext_deploy_task_id' : IDL.Text,
    'network' : IDL.Text,
    'nft_frontend_canister_id' : IDL.Text,
    'created_at' : IDL.Nat64,
    'error' : IDL.Text,
    'wasm_verified' : IDL.Int8,
    'token_frontend_canister_id' : IDL.Text,
    'job_id' : IDL.Text,
    'realm_name' : IDL.Text,
    'actual_wasm_hash' : IDL.Text,
    'caller_principal' : IDL.Text,
    'expected_assets_hash' : IDL.Text,
    'completed_at' : IDL.Nat64,
    'token_backend_canister_id' : IDL.Text,
    'frontend_canister_id' : IDL.Text,
    'nft_backend_canister_id' : IDL.Text,
  });
  const ResultJobIdStatus = IDL.Variant({
    'Ok' : DeploymentJobView,
    'Err' : InstallerError,
  });
  const PendingJobEntry = IDL.Record({
    'job' : DeploymentJobView,
    'manifest' : IDL.Text,
  });
  const PendingJobsOk = IDL.Record({
    'jobs' : IDL.Vec(PendingJobEntry),
    'count' : IDL.Nat32,
  });
  const ResultPendingJobs = IDL.Variant({
    'Ok' : PendingJobsOk,
    'Err' : InstallerError,
  });
  const VerificationReport = IDL.Record({
    'status' : IDL.Text,
    'expected_wasm_hash' : IDL.Text,
    'backend_canister_id' : IDL.Text,
    'wasm_verified' : IDL.Int8,
    'job_id' : IDL.Text,
    'actual_wasm_hash' : IDL.Text,
    'expected_assets_hash' : IDL.Text,
    'frontend_canister_id' : IDL.Text,
  });
  const ResultVerificationReport = IDL.Variant({
    'Ok' : VerificationReport,
    'Err' : InstallerError,
  });
  const HealthView = IDL.Record({
    'ok' : IDL.Bool,
    'max_registry_read_bytes' : IDL.Nat32,
    'max_upload_chunk_bytes' : IDL.Nat32,
    'canister' : IDL.Text,
  });
  const EndpointInfo = IDL.Record({
    'kind' : IDL.Text,
    'name' : IDL.Text,
    'description' : IDL.Text,
  });
  const InstallerInfoView = IDL.Record({
    'endpoints' : IDL.Vec(EndpointInfo),
    'name' : IDL.Text,
    'description' : IDL.Text,
    'version' : IDL.Text,
  });
  const InstallBackendOk = IDL.Record({
    'chunks_uploaded' : IDL.Nat32,
    'wasm_module_hash_hex' : IDL.Text,
    'mode' : IDL.Text,
    'wasm_namespace' : IDL.Text,
    'target_canister_id' : IDL.Text,
    'wasm_path' : IDL.Text,
    'wasm_size' : IDL.Nat64,
  });
  const ResultInstallBackend = IDL.Variant({
    'Ok' : InstallBackendOk,
    'Err' : InstallerError,
  });
  const ChildCanisterInstallStatus = IDL.Variant({
    'Empty' : IDL.Null,
    'Installed' : IDL.Null,
  });
  const ChildCanisterHistoryEntry = IDL.Record({
    'install_status' : ChildCanisterInstallStatus,
    'role' : IDL.Text,
    'canister_id' : IDL.Text,
    'created_at' : IDL.Nat64,
    'job_status' : IDL.Text,
    'job_id' : IDL.Text,
    'realm_name' : IDL.Text,
    'module_hash_hex' : IDL.Text,
  });
  const ChildCanisterHistoryOk = IDL.Record({
    'count' : IDL.Nat32,
    'entries' : IDL.Vec(ChildCanisterHistoryEntry),
  });
  const ResultChildCanisterHistory = IDL.Variant({
    'Ok' : ChildCanisterHistoryOk,
    'Err' : InstallerError,
  });
  const JobsListOk = IDL.Record({
    'jobs' : IDL.Vec(DeploymentJobView),
    'count' : IDL.Nat32,
  });
  const ResultJobsList = IDL.Variant({
    'Ok' : JobsListOk,
    'Err' : InstallerError,
  });
  const ReportReadyOk = IDL.Record({
    'status' : IDL.Text,
    'expected_wasm_hash' : IDL.Text,
    'failed_verification' : IDL.Bool,
    'extensions_started' : IDL.Bool,
    'wasm_verified' : IDL.Bool,
    'job_id' : IDL.Text,
    'actual_wasm_hash' : IDL.Text,
  });
  const ResultReportReady = IDL.Variant({
    'Ok' : ReportReadyOk,
    'Err' : InstallerError,
  });
  const ResultReportFailure = IDL.Variant({
    'Ok' : JobStatusAck,
    'Err' : InstallerError,
  });
  const VerifyOk = IDL.Record({
    'expected_wasm_hash' : IDL.Text,
    'verified' : IDL.Bool,
    'backend_canister_id' : IDL.Text,
    'module_hash' : IDL.Text,
    'reason' : IDL.Text,
  });
  const ResultVerify = IDL.Variant({ 'Ok' : VerifyOk, 'Err' : InstallerError });
  return IDL.Service({
    '__get_candid_interface_tmp_hack' : IDL.Func([], [IDL.Text], ['query']),
    'allocate_deployment_canisters' : IDL.Func(
        [IDL.Text],
        [ResultAllocate],
        [],
      ),
    'cancel_deployment' : IDL.Func([IDL.Text], [ResultJobCancel], []),
    'debug_resume_deploys' : IDL.Func([IDL.Text], [ResultDebugResume], []),
    'debug_run_one_step' : IDL.Func([IDL.Text], [ResultDebugRunStep], []),
    'enqueue_deployment' : IDL.Func([IDL.Text], [ResultEnqueue], []),
    'execute_code_shell' : IDL.Func([IDL.Text], [IDL.Text], []),
    'get_deployment_job_status' : IDL.Func(
        [IDL.Text],
        [ResultJobIdStatus],
        ['query'],
      ),
    'get_pending_deployments' : IDL.Func([], [ResultPendingJobs], ['query']),
    'get_verification_report' : IDL.Func(
        [IDL.Text],
        [ResultVerificationReport],
        ['query'],
      ),
    'health' : IDL.Func([], [HealthView], ['query']),
    'info' : IDL.Func([], [InstallerInfoView], ['query']),
    'list_child_canister_history' : IDL.Func(
        [],
        [ResultChildCanisterHistory],
        ['query'],
      ),
    'list_deployment_jobs' : IDL.Func([], [ResultJobsList], ['query']),
    'report_canister_ready' : IDL.Func([IDL.Text], [ResultReportReady], []),
    'report_deployment_failure' : IDL.Func(
        [IDL.Text],
        [ResultReportFailure],
        [],
      ),
    'verify_realm' : IDL.Func([IDL.Text], [ResultVerify], []),
  });
};
export const init = ({ IDL }) => { return []; };
