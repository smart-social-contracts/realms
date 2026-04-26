import type { Principal } from '@dfinity/principal';
import type { ActorMethod } from '@dfinity/agent';
import type { IDL } from '@dfinity/candid';

export interface Account {
  'owner' : Principal,
  'subaccount' : [] | [Uint8Array | number[]],
}
export interface AccountBalanceArgs { 'account' : Uint8Array | number[] }
export type AccountIdentifier = Uint8Array | number[];
export interface AccountTransaction {
  'id' : bigint,
  'transaction' : Transaction,
}
export type AddCreditsResult = { 'Ok' : UserCreditsRecord } |
  { 'Err' : string };
export type AddRealmResult = { 'Ok' : string } |
  { 'Err' : string };
export type Address = string;
export interface AppDataRecord {
  'scan_end_tx_id' : bigint,
  'max_results' : bigint,
  'scan_start_tx_id' : bigint,
  'scan_oldest_tx_id' : bigint,
  'sync_tx_id' : bigint,
  'max_iteration_count' : bigint,
  'admin_principal' : Principal,
  'sync_status' : string,
}
export interface Approve {
  'fee' : [] | [bigint],
  'from' : Account,
  'memo' : [] | [Array<bigint>],
  'created_at_time' : [] | [bigint],
  'amount' : bigint,
  'expected_allowance' : [] | [bigint],
  'expires_at' : [] | [bigint],
  'spender' : Spender,
}
export interface Archive { 'canister_id' : Principal }
export interface Archives { 'archives' : Array<Archive> }
export interface AssetCanisterService {
  'commit_batch' : ActorMethod<[string], undefined>,
  'create_batch' : ActorMethod<[string], string>,
  'create_chunk' : ActorMethod<[string], string>,
}
export interface AssistantInput {
  'categories' : string,
  'eval_report_url' : string,
  'training_data_summary' : string,
  'requested_role' : string,
  'icon' : string,
  'name' : string,
  'requested_permissions' : string,
  'languages' : string,
  'description' : string,
  'version' : string,
  'endpoint_url' : string,
  'domains' : string,
  'assistant_id' : string,
  'base_model' : string,
  'file_registry_canister_id' : string,
  'price_e8s' : bigint,
  'runtime' : string,
  'file_registry_namespace' : string,
  'pricing_summary' : string,
}
export interface AssistantListResult {
  'per_page' : bigint,
  'listings' : Array<AssistantListing>,
  'page' : bigint,
  'total_count' : bigint,
}
export interface AssistantListing {
  'categories' : string,
  'eval_report_url' : string,
  'training_data_summary' : string,
  'requested_role' : string,
  'updated_at' : number,
  'icon' : string,
  'name' : string,
  'verification_notes' : string,
  'requested_permissions' : string,
  'languages' : string,
  'installs' : bigint,
  'description' : string,
  'created_at' : number,
  'verification_status' : string,
  'likes' : bigint,
  'version' : string,
  'endpoint_url' : string,
  'domains' : string,
  'assistant_id' : string,
  'base_model' : string,
  'assistant_alias' : string,
  'is_active' : boolean,
  'file_registry_canister_id' : string,
  'price_e8s' : bigint,
  'runtime' : string,
  'file_registry_namespace' : string,
  'developer' : string,
  'pricing_summary' : string,
}
export type AssistantResult = { 'Ok' : AssistantListing } |
  { 'Err' : string };
export interface BadBurnRecord { 'min_burn_amount' : bigint }
export interface BadFeeRecord { 'expected_fee' : bigint }
export interface BalanceRecord { 'principal_id' : Principal, 'amount' : bigint }
export interface BillingStatusRecord {
  'total_spent' : bigint,
  'total_balance' : bigint,
  'total_purchased' : bigint,
  'users_count' : bigint,
}
export type BitcoinAddress = string;
export type BitcoinNetwork = { 'Mainnet' : null } |
  { 'Regtest' : null } |
  { 'Testnet' : null };
export interface Block {
  'transaction' : Transaction,
  'timestamp' : TimeStamp,
  'parent_hash' : [] | [Uint8Array | number[]],
}
export type BlockHash = Uint8Array | number[];
export type BlockIndex = bigint;
export interface BlockRange { 'blocks' : Array<Block> }
export interface Burn {
  'from' : Account,
  'memo' : [] | [Array<bigint>],
  'created_at_time' : [] | [bigint],
  'amount' : bigint,
  'spender' : [] | [Spender],
}
export type Callback = ActorMethod<
  [StreamingToken],
  StreamingCallbackHttpResponse
>;
export interface CallbackStrategy {
  'token' : StreamingToken,
  'callback' : Callback,
}
export interface CanisterInfo {
  'canister_id' : string,
  'canister_type' : string,
}
export interface CanisterRecord { 'id' : string, 'principal' : Principal }
export interface CanisterSettings {
  'freezing_threshold' : [] | [bigint],
  'controllers' : [] | [Array<Principal>],
  'memory_allocation' : [] | [bigint],
  'compute_allocation' : [] | [bigint],
}
export type CanisterStatus = { 'stopped' : null } |
  { 'stopping' : null } |
  { 'running' : null };
export interface CanisterStatusArgs { 'canister_id' : Principal }
export interface CanisterStatusResult {
  'status' : CanisterStatus,
  'memory_size' : bigint,
  'cycles' : bigint,
  'settings' : DefiniteCanisterSettings,
  'module_hash' : [] | [Uint8Array | number[]],
}
export interface CodexInput {
  'categories' : string,
  'icon' : string,
  'name' : string,
  'description' : string,
  'version' : string,
  'codex_id' : string,
  'realm_type' : string,
  'file_registry_canister_id' : string,
  'price_e8s' : bigint,
  'file_registry_namespace' : string,
}
export interface CodexListResult {
  'per_page' : bigint,
  'listings' : Array<CodexListing>,
  'page' : bigint,
  'total_count' : bigint,
}
export interface CodexListing {
  'categories' : string,
  'updated_at' : number,
  'icon' : string,
  'name' : string,
  'verification_notes' : string,
  'installs' : bigint,
  'description' : string,
  'created_at' : number,
  'verification_status' : string,
  'likes' : bigint,
  'version' : string,
  'codex_id' : string,
  'realm_type' : string,
  'is_active' : boolean,
  'file_registry_canister_id' : string,
  'codex_alias' : string,
  'price_e8s' : bigint,
  'file_registry_namespace' : string,
  'developer' : string,
}
export type CodexResult = { 'Ok' : CodexListing } |
  { 'Err' : string };
export interface ConfigRecord {
  'billing_service_principal' : string,
  'license_price_usd_cents' : bigint,
  'license_duration_seconds' : bigint,
  'file_registry_canister_id' : string,
}
export type ConfigResult = { 'Ok' : ConfigRecord } |
  { 'Err' : string };
export interface CreateCanisterArgs { 'settings' : [] | [CanisterSettings] }
export interface CreateCanisterResult { 'canister_id' : Principal }
export interface CreditTransactionRecord {
  'id' : string,
  'transaction_type' : string,
  'description' : string,
  'timestamp' : number,
  'stripe_session_id' : string,
  'principal_id' : string,
  'amount' : bigint,
}
export interface CryptoResponse {
  'data' : CryptoResponseData,
  'success' : boolean,
}
export type CryptoResponseData = { 'scopeList' : ScopeListRecord } |
  { 'envelope' : EnvelopeRecord } |
  { 'error' : string } |
  { 'envelopeList' : EnvelopeListRecord } |
  { 'groupMembers' : GroupMembersRecord } |
  { 'group' : GroupRecord } |
  { 'message' : string } |
  { 'groupList' : GroupListRecord };
export interface DecimalsResult { 'decimals' : number }
export type DeductCreditsResult = { 'Ok' : UserCreditsRecord } |
  { 'Err' : string };
export interface DefiniteCanisterSettings {
  'freezing_threshold' : bigint,
  'controllers' : Array<Principal>,
  'memory_allocation' : bigint,
  'compute_allocation' : bigint,
}
export interface DeleteCanisterArgs { 'canister_id' : Principal }
export interface DepositCyclesArgs { 'canister_id' : Principal }
export interface DeveloperLicense {
  'last_payment_amount_usd_cents' : bigint,
  'principal' : string,
  'note' : string,
  'last_payment_id' : string,
  'created_at' : number,
  'payment_method' : string,
  'is_active' : boolean,
  'expires_at' : number,
}
export interface DuplicateRecord { 'duplicate_of' : bigint }
export type EcdsaCurve = { 'secp256k1' : null };
export interface EcdsaPublicKeyArgs {
  'key_id' : KeyId,
  'canister_id' : [] | [Principal],
  'derivation_path' : Array<Uint8Array | number[]>,
}
export interface EcdsaPublicKeyResult {
  'public_key' : Uint8Array | number[],
  'chain_code' : Uint8Array | number[],
}
export interface EnvelopeListRecord { 'envelopes' : Array<EnvelopeRecord> }
export interface EnvelopeRecord {
  'scope' : string,
  'principal_id' : string,
  'wrapped_dek' : string,
}
export interface ExtensionCallArgs {
  'args' : string,
  'function_name' : string,
  'extension_name' : string,
}
export interface ExtensionCallResponse {
  'response' : string,
  'success' : boolean,
}
export interface ExtensionInput {
  'categories' : string,
  'extension_id' : string,
  'icon' : string,
  'name' : string,
  'download_url' : string,
  'description' : string,
  'version' : string,
  'file_registry_canister_id' : string,
  'price_e8s' : bigint,
  'file_registry_namespace' : string,
}
export interface ExtensionListResult {
  'per_page' : bigint,
  'listings' : Array<ExtensionListing>,
  'page' : bigint,
  'total_count' : bigint,
}
export interface ExtensionListing {
  'categories' : string,
  'updated_at' : number,
  'extension_id' : string,
  'icon' : string,
  'name' : string,
  'verification_notes' : string,
  'installs' : bigint,
  'download_url' : string,
  'description' : string,
  'created_at' : number,
  'verification_status' : string,
  'likes' : bigint,
  'version' : string,
  'is_active' : boolean,
  'file_registry_canister_id' : string,
  'price_e8s' : bigint,
  'file_registry_namespace' : string,
  'developer' : string,
}
export type ExtensionResult = { 'Ok' : ExtensionListing } |
  { 'Err' : string };
export interface ExtensionsListRecord { 'extensions' : Array<string> }
export interface FileRegistryService {
  'get_backend_files_icc' : ActorMethod<[string, string, string], string>,
  'get_extension_manifest' : ActorMethod<[string], string>,
}
export interface GenericError { 'message' : string, 'error_code' : bigint }
export interface GenericErrorRecord {
  'message' : string,
  'error_code' : bigint,
}
export type GenericResult = { 'Ok' : string } |
  { 'Err' : string };
export interface GetAccountTransactionsRequest {
  'max_results' : bigint,
  'start' : [] | [bigint],
  'account' : Account,
}
export interface GetAccountTransactionsResponse {
  'balance' : bigint,
  'transactions' : Array<AccountTransaction>,
  'oldest_tx_id' : [] | [bigint],
}
export interface GetBalanceArgs {
  'network' : BitcoinNetwork,
  'address' : string,
  'min_confirmations' : [] | [number],
}
export type GetBillingStatusResult = { 'Ok' : BillingStatusRecord } |
  { 'Err' : string };
export interface GetBlocksArgs { 'start' : bigint, 'length' : bigint }
export type GetCreditsResult = { 'Ok' : UserCreditsRecord } |
  { 'Err' : string };
export interface GetCurrentFeePercentilesArgs { 'network' : BitcoinNetwork }
export type GetRealmResult = { 'Ok' : RealmRecord } |
  { 'Err' : string };
export type GetStatusResult = { 'Ok' : StatusRecord } |
  { 'Err' : string };
export type GetTransactionsResult = { 'Ok' : GetAccountTransactionsResponse } |
  { 'Err' : string };
export interface GetUtxosArgs {
  'network' : BitcoinNetwork,
  'filter' : [] | [UtxosFilter],
  'address' : string,
}
export interface GetUtxosResult {
  'next_page' : [] | [Uint8Array | number[]],
  'tip_height' : number,
  'tip_block_hash' : Uint8Array | number[],
  'utxos' : Array<Utxo>,
}
export interface GroupListRecord { 'groups' : Array<GroupRecord> }
export interface GroupMemberRecord { 'role' : string, 'principal_id' : string }
export interface GroupMembersRecord { 'members' : Array<GroupMemberRecord> }
export interface GroupRecord { 'name' : string, 'description' : string }
export type GuardResult = { 'Ok' : null } |
  { 'Err' : string };
export type Header = [string, string];
export interface HttpHeader { 'value' : string, 'name' : string }
export type HttpMethod = { 'get' : null } |
  { 'head' : null } |
  { 'post' : null };
export interface HttpRequest {
  'url' : string,
  'method' : string,
  'body' : Uint8Array | number[],
  'headers' : Array<Header>,
}
export interface HttpRequestArgs {
  'url' : string,
  'method' : HttpMethod,
  'max_response_bytes' : [] | [bigint],
  'body' : [] | [Uint8Array | number[]],
  'transform' : [] | [HttpTransform],
  'headers' : Array<HttpHeader>,
}
export interface HttpResponse {
  'status' : bigint,
  'body' : Uint8Array | number[],
  'headers' : Array<HttpHeader>,
}
export interface HttpResponseIncoming {
  'body' : Uint8Array | number[],
  'headers' : Array<Header>,
  'upgrade' : [] | [boolean],
  'streaming_strategy' : [] | [StreamingStrategy],
  'status_code' : number,
}
export interface HttpTransform {
  'function' : HttpTransformFunc,
  'context' : Uint8Array | number[],
}
export interface HttpTransformArgs {
  'context' : Uint8Array | number[],
  'response' : HttpResponse,
}
export type HttpTransformFunc = ActorMethod<[HttpTransformArgs], HttpResponse>;
export interface ICRCIndexer {
  'get_account_transactions' : ActorMethod<
    [GetAccountTransactionsRequest],
    GetTransactionsResult
  >,
}
export interface ICRCLedger {
  'icrc1_balance_of' : ActorMethod<[Account], bigint>,
  'icrc1_fee' : ActorMethod<[], bigint>,
  'icrc1_transfer' : ActorMethod<[TransferArg], TransferResult>,
}
export type InsertError = {
    'ValueTooLarge' : { 'max' : number, 'given' : number }
  } |
  { 'KeyTooLarge' : { 'max' : number, 'given' : number } };
export interface InstallCodeArgs {
  'arg' : Uint8Array | number[],
  'wasm_module' : Uint8Array | number[],
  'mode' : InstallCodeMode,
  'canister_id' : Principal,
}
export type InstallCodeMode = { 'reinstall' : null } |
  { 'upgrade' : null } |
  { 'install' : null };
export interface InsufficientFundsRecord { 'balance' : bigint }
export interface KeyId { 'name' : string, 'curve' : EcdsaCurve }
export interface KeyTooLarge { 'max' : number, 'given' : number }
export interface LLMChatResponse { 'response' : string }
export interface LicensePaymentInput {
  'principal' : string,
  'duration_seconds' : bigint,
  'note' : string,
  'payment_method' : string,
  'stripe_session_id' : string,
  'amount_usd_cents' : bigint,
}
export interface LicensePricingRecord {
  'license_price_usd_cents' : bigint,
  'license_duration_seconds' : bigint,
}
export type LicenseResult = { 'Ok' : DeveloperLicense } |
  { 'Err' : string };
export interface LikeRecord {
  'item_kind' : string,
  'created_at' : number,
  'item_id' : string,
}
export interface MarketplaceInitArg {
  'billing_service_principal' : [] | [string],
  'file_registry' : [] | [string],
}
export type Memo = bigint;
export type MetadataValue = { 'Int' : bigint } |
  { 'Nat' : bigint } |
  { 'Blob' : Uint8Array | number[] } |
  { 'Text' : string };
export type MillisatoshiPerByte = bigint;
export interface Mint {
  'to' : Account,
  'memo' : [] | [Array<bigint>],
  'created_at_time' : [] | [bigint],
  'amount' : bigint,
}
export interface MintArg {
  'token_id' : bigint,
  'owner' : NftAccount,
  'metadata' : [] | [Array<[string, MetadataValue]>],
}
export type MintError = { 'GenericError' : GenericError } |
  { 'SupplyCapReached' : null } |
  { 'Unauthorized' : null } |
  { 'TokenIdAlreadyExists' : null };
export type MintResult = { 'Ok' : bigint } |
  { 'Err' : MintError };
export interface NFTService { 'mint' : ActorMethod<[MintArg], MintResult> }
export interface NameResult { 'name' : string }
export interface NftAccount {
  'owner' : Principal,
  'subaccount' : [] | [Uint8Array | number[]],
}
export type NotifyResult = { 'Ok' : null } |
  {
    'Err' : { 'NoError' : null } |
      { 'CanisterError' : null } |
      { 'SysTransient' : null } |
      { 'DestinationInvalid' : null } |
      { 'SysFatal' : null } |
      { 'CanisterReject' : null }
  };
export interface ObjectsListRecord { 'objects' : Array<string> }
export interface ObjectsListRecordPaginated {
  'pagination' : PaginationInfo,
  'objects' : Array<string>,
}
export type Operation = { 'Burn' : Operation_Burn } |
  { 'Mint' : Operation_Mint } |
  { 'Transfer' : Operation_Transfer };
export interface Operation_Burn {
  'from' : Uint8Array | number[],
  'amount' : Tokens,
}
export interface Operation_Mint {
  'to' : Uint8Array | number[],
  'amount' : Tokens,
}
export interface Operation_Transfer {
  'to' : Uint8Array | number[],
  'fee' : Tokens,
  'from' : Uint8Array | number[],
  'amount' : Tokens,
}
export interface Outpoint { 'txid' : Uint8Array | number[], 'vout' : number }
export type Page = Uint8Array | number[];
export interface PaginationInfo {
  'page_size' : bigint,
  'total_pages' : bigint,
  'total_items_count' : bigint,
  'page_num' : bigint,
}
export interface PendingAudit {
  'updated_at' : number,
  'name' : string,
  'item_kind' : string,
  'version' : string,
  'item_id' : string,
  'developer' : string,
}
export interface ProvisionalCreateCanisterWithCyclesArgs {
  'settings' : [] | [CanisterSettings],
  'amount' : [] | [bigint],
}
export interface ProvisionalCreateCanisterWithCyclesResult {
  'canister_id' : Principal,
}
export interface ProvisionalTopUpCanisterArgs {
  'canister_id' : Principal,
  'amount' : bigint,
}
export interface PurchaseRecord {
  'purchased_at' : number,
  'item_kind' : string,
  'purchase_id' : string,
  'realm_principal' : string,
  'price_paid_e8s' : bigint,
  'item_id' : string,
  'developer' : string,
}
export interface QuarterInfoRecord {
  'status' : string,
  'name' : string,
  'canister_id' : string,
  'population' : bigint,
}
export type QueryArchiveError = {
    'BadFirstBlockIndex' : QueryArchiveError_BadFirstBlockIndex
  } |
  { 'Other' : QueryArchiveError_Other };
export interface QueryArchiveError_BadFirstBlockIndex {
  'requested_index' : bigint,
  'first_valid_index' : bigint,
}
export interface QueryArchiveError_Other {
  'error_message' : string,
  'error_code' : bigint,
}
export type QueryArchiveFn = ActorMethod<[GetBlocksArgs], QueryArchiveResult>;
export type QueryArchiveResult = { 'Ok' : BlockRange } |
  { 'Err' : QueryArchiveError };
export interface QueryBlocksResponse {
  'certificate' : [] | [Uint8Array | number[]],
  'blocks' : Array<Block>,
  'chain_length' : bigint,
  'first_block_index' : bigint,
  'archived_blocks' : Array<QueryBlocksResponse_archived_blocks>,
}
export interface QueryBlocksResponse_archived_blocks {
  'callback' : QueryArchiveFn,
  'start' : bigint,
  'length' : bigint,
}
export interface RealmData {
  'json' : string,
  'timestamp' : bigint,
  'principal_id' : string,
}
export interface RealmRecord {
  'id' : string,
  'url' : string,
  'logo' : string,
  'name' : string,
  'created_at' : number,
  'backend_url' : string,
  'users_count' : bigint,
}
export interface RealmRegistryService {
  'register_realm' : ActorMethod<
    [string, string, string, string, string],
    AddRealmResult
  >,
}
export interface RealmResponse {
  'data' : RealmResponseData,
  'success' : boolean,
}
export type RealmResponseData = { 'status' : StatusRecord } |
  { 'objectsListPaginated' : ObjectsListRecordPaginated } |
  { 'objectsList' : ObjectsListRecord } |
  { 'extensionsList' : ExtensionsListRecord } |
  { 'userGet' : UserGetRecord } |
  { 'error' : string } |
  { 'message' : string };
export interface RealmTargetService {
  'install_codex_from_registry' : ActorMethod<[string], string>,
  'install_extension_from_registry' : ActorMethod<[string], string>,
}
export interface RealmsListRecord {
  'total_count' : bigint,
  'realms' : Array<RealmRecord>,
}
export type RejectionCode = { 'NoError' : null } |
  { 'CanisterError' : null } |
  { 'SysTransient' : null } |
  { 'DestinationInvalid' : null } |
  { 'SysFatal' : null } |
  { 'CanisterReject' : null };
export interface Response { 'data' : ResponseData, 'success' : boolean }
export type ResponseData = { 'Error' : string } |
  { 'Stats' : StatsRecord } |
  { 'TestMode' : TestModeRecord } |
  { 'TransactionId' : TransactionIdRecord } |
  { 'Message' : string } |
  { 'Transactions' : Array<TransactionRecord> } |
  { 'TransactionSummary' : TransactionSummaryRecord } |
  { 'Balance' : BalanceRecord };
export type Satoshi = bigint;
export interface ScopeListRecord { 'scopes' : Array<string> }
export interface SearchRealmsResult {
  'count' : bigint,
  'query' : string,
  'realms' : Array<RealmRecord>,
}
export interface SendTransactionArgs {
  'transaction' : Uint8Array | number[],
  'network' : BitcoinNetwork,
}
export type SendTransactionError = { 'QueueFull' : null } |
  { 'MalformedTransaction' : null };
export interface SignWithEcdsaArgs {
  'key_id' : KeyId,
  'derivation_path' : Array<Uint8Array | number[]>,
  'message_hash' : Uint8Array | number[],
}
export interface SignWithEcdsaResult { 'signature' : Uint8Array | number[] }
export interface Spender {
  'owner' : Principal,
  'subaccount' : [] | [Uint8Array | number[]],
}
export type Stable64GrowResult = { 'Ok' : bigint } |
  { 'Err' : { 'OutOfBounds' : null } | { 'OutOfMemory' : null } };
export type StableGrowResult = { 'Ok' : number } |
  { 'Err' : { 'OutOfBounds' : null } | { 'OutOfMemory' : null } };
export type StableMemoryError = { 'OutOfBounds' : null } |
  { 'OutOfMemory' : null };
export interface StartCanisterArgs { 'canister_id' : Principal }
export interface StatsRecord {
  'app_data' : AppDataRecord,
  'canisters' : Array<CanisterRecord>,
  'balances' : Array<BalanceRecord>,
}
export interface StatusRecord {
  'python_version' : string,
  'status' : string,
  'transfers_count' : bigint,
  'codexes_count' : bigint,
  'is_quarter' : boolean,
  'proposals_count' : bigint,
  'test_mode' : boolean,
  'realms_count' : bigint,
  'version' : string,
  'extensions' : Array<string>,
  'disputes_count' : bigint,
  'realm_welcome_message' : string,
  'accounting_currency_decimals' : bigint,
  'canisters' : Array<CanisterInfo>,
  'realm_logo' : string,
  'realm_name' : string,
  'dependencies' : Array<string>,
  'user_profiles_count' : bigint,
  'commit' : string,
  'instruments_count' : bigint,
  'organizations_count' : bigint,
  'realm_welcome_image' : string,
  'mandates_count' : bigint,
  'tasks_count' : bigint,
  'votes_count' : bigint,
  'licenses_count' : bigint,
  'commit_datetime' : string,
  'users_count' : bigint,
  'parent_realm_canister_id' : string,
  'realm_description' : string,
  'trades_count' : bigint,
  'accounting_currency' : string,
  'quarters' : Array<QuarterInfoRecord>,
  'registries' : Array<CanisterInfo>,
}
export type StatusResult = { 'Ok' : StatusRecord } |
  { 'Err' : string };
export interface StopCanisterArgs { 'canister_id' : Principal }
export interface StreamingCallbackHttpResponse {
  'token' : [] | [StreamingToken],
  'body' : Uint8Array | number[],
}
export type StreamingStrategy = { 'Callback' : CallbackStrategy };
export interface StreamingToken { 'key' : string }
export type SubAccount = Uint8Array | number[];
export interface SymbolResult { 'symbol' : string }
export interface TestBenchResponse { 'data' : string }
export interface TestModeRecord {
  'tx_id' : bigint,
  'test_mode_enabled' : boolean,
}
export interface TimeStamp { 'timestamp_nanos' : bigint }
export interface Tokens { 'e8s' : bigint }
export interface Transaction {
  'burn' : [] | [Burn],
  'kind' : string,
  'mint' : [] | [Mint],
  'approve' : [] | [Approve],
  'timestamp' : bigint,
  'transfer' : [] | [Transfer],
}
export type TransactionHistoryResult = {
    'Ok' : Array<CreditTransactionRecord>
  } |
  { 'Err' : string };
export interface TransactionIdRecord { 'transaction_id' : bigint }
export interface TransactionRecord {
  'id' : bigint,
  'kind' : string,
  'principal_from' : Principal,
  'timestamp' : bigint,
  'principal_to' : Principal,
  'amount' : bigint,
}
export interface TransactionSummaryRecord {
  'scan_end_tx_id' : bigint,
  'new_txs_count' : bigint,
  'sync_status' : string,
}
export interface TransactionsListRecord {
  'transactions' : Array<TransactionRecord>,
}
export interface Transfer {
  'to' : Account,
  'fee' : [] | [bigint],
  'from' : Account,
  'memo' : [] | [Array<bigint>],
  'created_at_time' : [] | [bigint],
  'amount' : bigint,
  'spender' : [] | [Spender],
}
export interface TransferArg {
  'to' : Account,
  'fee' : [] | [bigint],
  'memo' : [] | [bigint],
  'from_subaccount' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [bigint],
  'amount' : bigint,
}
export interface TransferArgs {
  'to' : Uint8Array | number[],
  'fee' : Tokens,
  'memo' : bigint,
  'from_subaccount' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [TimeStamp],
  'amount' : Tokens,
}
export type TransferError = { 'GenericError' : GenericErrorRecord } |
  { 'TemporarilyUnavailable' : null } |
  { 'BadBurn' : BadBurnRecord } |
  { 'Duplicate' : DuplicateRecord } |
  { 'BadFee' : BadFeeRecord } |
  { 'CreatedInFuture' : null } |
  { 'TooOld' : null } |
  { 'InsufficientFunds' : InsufficientFundsRecord };
export interface TransferError_BadFee { 'expected_fee' : Tokens }
export interface TransferError_InsufficientFunds { 'balance' : Tokens }
export interface TransferError_TxDuplicate { 'duplicate_of' : bigint }
export interface TransferError_TxTooOld { 'allowed_window_nanos' : bigint }
export interface TransferFee { 'transfer_fee' : Tokens }
export type TransferFeeArg = {};
export type TransferResult = { 'Ok' : bigint } |
  { 'Err' : TransferError };
export interface UninstallCodeArgs { 'canister_id' : Principal }
export interface UpdateSettingsArgs {
  'canister_id' : Principal,
  'settings' : CanisterSettings,
}
export interface UserCreditsRecord {
  'total_spent' : bigint,
  'balance' : bigint,
  'principal_id' : string,
  'total_purchased' : bigint,
}
export interface UserGetRecord {
  'assigned_quarter' : string,
  'principal' : Principal,
  'private_data' : string,
  'nickname' : string,
  'profiles' : Array<string>,
  'avatar' : string,
}
export interface Utxo {
  'height' : number,
  'value' : bigint,
  'outpoint' : Outpoint,
}
export type UtxosFilter = { 'Page' : Uint8Array | number[] } |
  { 'MinConfirmations' : number };
export interface ValueTooLarge { 'max' : number, 'given' : number }
export interface _SERVICE {
  '__get_candid_interface_tmp_hack' : ActorMethod<[], string>,
  'change_quarter' : ActorMethod<[string], RealmResponse>,
  'check_verification_status' : ActorMethod<[string], string>,
  'create_multi_step_scheduled_task' : ActorMethod<
    [string, string, bigint, bigint],
    string
  >,
  'crypto_add_group_member' : ActorMethod<
    [string, string, string],
    CryptoResponse
  >,
  'crypto_create_group' : ActorMethod<[string, string], CryptoResponse>,
  'crypto_delete_group' : ActorMethod<[string], CryptoResponse>,
  'crypto_get_envelopes' : ActorMethod<[string], CryptoResponse>,
  'crypto_get_group_members' : ActorMethod<[string], CryptoResponse>,
  'crypto_get_my_envelope' : ActorMethod<[string], CryptoResponse>,
  'crypto_get_my_scopes' : ActorMethod<[], CryptoResponse>,
  'crypto_list_groups' : ActorMethod<[], CryptoResponse>,
  'crypto_remove_group_member' : ActorMethod<[string, string], CryptoResponse>,
  'crypto_revoke' : ActorMethod<[string, string], CryptoResponse>,
  'crypto_revoke_from_group' : ActorMethod<[string, string], CryptoResponse>,
  'crypto_share' : ActorMethod<[string, string, string], CryptoResponse>,
  'crypto_share_with_group' : ActorMethod<[string, string], CryptoResponse>,
  'crypto_store_my_envelope' : ActorMethod<[string, string], CryptoResponse>,
  'declare_independence' : ActorMethod<[], RealmResponse>,
  'deregister_quarter' : ActorMethod<[string], RealmResponse>,
  'derive_my_vetkey' : ActorMethod<[string], RealmResponse>,
  'execute_code_shell' : ActorMethod<[string], string>,
  'extension_async_call' : ActorMethod<
    [ExtensionCallArgs],
    ExtensionCallResponse
  >,
  'extension_call' : ActorMethod<[ExtensionCallArgs], ExtensionCallResponse>,
  'extension_sync_call' : ActorMethod<
    [ExtensionCallArgs],
    ExtensionCallResponse
  >,
  'find_objects' : ActorMethod<
    [string, Array<[string, string]>],
    RealmResponse
  >,
  'get_canister_id' : ActorMethod<[], string>,
  'get_current_application_id' : ActorMethod<[string], string>,
  'get_extension_frontend_info' : ActorMethod<[string], string>,
  'get_extensions' : ActorMethod<[], RealmResponse>,
  'get_my_invoices' : ActorMethod<[], RealmResponse>,
  'get_my_principal' : ActorMethod<[], string>,
  'get_my_user_status' : ActorMethod<[], RealmResponse>,
  'get_my_vetkey_public_key' : ActorMethod<[], RealmResponse>,
  'get_nft_config' : ActorMethod<[], string>,
  'get_objects' : ActorMethod<[Array<[string, string]>], RealmResponse>,
  'get_objects_paginated' : ActorMethod<
    [string, bigint, bigint, string],
    RealmResponse
  >,
  'get_quarter_info' : ActorMethod<[], RealmResponse>,
  'get_realm_registry_info' : ActorMethod<[], string>,
  'get_sidebar_manifests' : ActorMethod<[], string>,
  'get_verification_link' : ActorMethod<[string], string>,
  'get_zones' : ActorMethod<[bigint], string>,
  'http_request' : ActorMethod<[HttpRequest], HttpResponseIncoming>,
  'http_transform' : ActorMethod<[HttpTransformArgs], HttpResponse>,
  'install_codex' : ActorMethod<[string], string>,
  'install_codex_from_registry' : ActorMethod<[string], string>,
  'install_extension' : ActorMethod<[string], string>,
  'install_extension_from_registry' : ActorMethod<[string], string>,
  'join_federation' : ActorMethod<[string, boolean], RealmResponse>,
  'join_realm' : ActorMethod<[string, string], RealmResponse>,
  'list_codex_packages' : ActorMethod<[], string>,
  'list_extensions' : ActorMethod<[string], RealmResponse>,
  'list_runtime_extensions' : ActorMethod<[], string>,
  'mint_land_nft_for_parcel' : ActorMethod<
    [string, string, bigint, string],
    string
  >,
  'refresh_invoice' : ActorMethod<[string], string>,
  'register_quarter' : ActorMethod<[string, string], RealmResponse>,
  'register_realm_with_registry' : ActorMethod<
    [string, string, string, string, string],
    string
  >,
  'reload_codex' : ActorMethod<[string], string>,
  'reload_entity_method_overrides' : ActorMethod<[], string>,
  'set_application_id' : ActorMethod<[string], string>,
  'set_canister_config' : ActorMethod<
    [[] | [string], [] | [string], [] | [string]],
    RealmResponse
  >,
  'set_quarter_config' : ActorMethod<[string], RealmResponse>,
  'start_task_manager' : ActorMethod<[], string>,
  'status' : ActorMethod<[], RealmResponse>,
  'test_timer' : ActorMethod<[], string>,
  'uninstall_codex' : ActorMethod<[string], string>,
  'uninstall_extension' : ActorMethod<[string], string>,
  'update_my_private_data' : ActorMethod<[string], RealmResponse>,
  'update_my_public_profile' : ActorMethod<[string, string], RealmResponse>,
  'update_realm_config' : ActorMethod<[string], string>,
}
export declare const idlFactory: IDL.InterfaceFactory;
export declare const init: (args: { IDL: typeof IDL }) => IDL.Type[];
