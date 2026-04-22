export interface RealmRecord {
  id: string;
  name: string;
  url: string;
  backend_url: string;
  logo: string;
  users_count: number;
  created_at: string;
}

export interface CanisterInfo {
  canister_id: string;
  canister_type: string;
  name?: string;
}

export interface QuarterInfoRecord {
  name: string;
  canister_id: string;
  population: number;
  status: string;
}

export interface StatusRecord {
  version?: string;
  commit?: string;
  canisters?: CanisterInfo[];
  quarters?: QuarterInfoRecord[];
  registries?: CanisterInfo[];
  users_count?: number;
  objects_count?: number;
  extensions?: string[];
  realms_count?: number;
  dependencies?: Record<string, string>;
  is_caller_controller?: boolean;
  [key: string]: any;
}

export interface DeployRecord {
  deploy_id: string;
  realm_name: string;
  status: string;
  started_at: string;
  completed_at?: string;
  error?: string;
}

export interface DeployStepRecord {
  step: number;
  name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  log?: string;
}

export interface DeployStatusRecord {
  deploy_id: string;
  realm_name: string;
  status: string;
  steps: DeployStepRecord[];
  error?: string;
}

export interface FileRegistryStats {
  total_files: number;
  total_bytes: number;
  total_chunks: number;
}

export interface InstallerInfo {
  version: string;
  commit?: string;
  [key: string]: any;
}

export interface DeploymentJob {
  job_id: string;
  status: string;
  caller_principal: string;
  network: string;
  backend_canister_id: string;
  frontend_canister_id: string;
  expected_wasm_hash: string;
  expected_assets_hash: string;
  actual_wasm_hash: string;
  wasm_verified: number;
  error: string;
  created_at: number;
  completed_at: number;
}

export interface VerificationReport {
  job_id: string;
  backend_canister_id: string;
  frontend_canister_id: string;
  expected_wasm_hash: string;
  expected_assets_hash: string;
  actual_wasm_hash: string;
  wasm_verified: number;
  status: string;
}
