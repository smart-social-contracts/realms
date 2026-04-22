export const idlFactory = ({ IDL }) => {
  const CanisterInfo = IDL.Record({
    'canister_id' : IDL.Text,
    'canister_type' : IDL.Text,
  });
  const QuarterInfoRecord = IDL.Record({
    'status' : IDL.Text,
    'name' : IDL.Text,
    'canister_id' : IDL.Text,
    'population' : IDL.Nat,
  });
  const StatusRecord = IDL.Record({
    'python_version' : IDL.Text,
    'status' : IDL.Text,
    'transfers_count' : IDL.Nat,
    'codexes_count' : IDL.Nat,
    'is_quarter' : IDL.Bool,
    'proposals_count' : IDL.Nat,
    'test_mode' : IDL.Bool,
    'realms_count' : IDL.Nat,
    'version' : IDL.Text,
    'extensions' : IDL.Vec(IDL.Text),
    'disputes_count' : IDL.Nat,
    'realm_welcome_message' : IDL.Text,
    'accounting_currency_decimals' : IDL.Nat,
    'canisters' : IDL.Vec(CanisterInfo),
    'realm_logo' : IDL.Text,
    'realm_name' : IDL.Text,
    'dependencies' : IDL.Vec(IDL.Text),
    'user_profiles_count' : IDL.Nat,
    'commit' : IDL.Text,
    'instruments_count' : IDL.Nat,
    'organizations_count' : IDL.Nat,
    'realm_welcome_image' : IDL.Text,
    'mandates_count' : IDL.Nat,
    'tasks_count' : IDL.Nat,
    'votes_count' : IDL.Nat,
    'licenses_count' : IDL.Nat,
    'commit_datetime' : IDL.Text,
    'users_count' : IDL.Nat,
    'parent_realm_canister_id' : IDL.Text,
    'realm_description' : IDL.Text,
    'trades_count' : IDL.Nat,
    'accounting_currency' : IDL.Text,
    'quarters' : IDL.Vec(QuarterInfoRecord),
    'registries' : IDL.Vec(CanisterInfo),
  });
  const PaginationInfo = IDL.Record({
    'page_size' : IDL.Int,
    'total_pages' : IDL.Int,
    'total_items_count' : IDL.Int,
    'page_num' : IDL.Int,
  });
  const ObjectsListRecordPaginated = IDL.Record({
    'pagination' : PaginationInfo,
    'objects' : IDL.Vec(IDL.Text),
  });
  const ObjectsListRecord = IDL.Record({ 'objects' : IDL.Vec(IDL.Text) });
  const ExtensionsListRecord = IDL.Record({ 'extensions' : IDL.Vec(IDL.Text) });
  const UserGetRecord = IDL.Record({
    'assigned_quarter' : IDL.Text,
    'principal' : IDL.Principal,
    'private_data' : IDL.Text,
    'nickname' : IDL.Text,
    'profiles' : IDL.Vec(IDL.Text),
    'avatar' : IDL.Text,
  });
  const RealmResponseData = IDL.Variant({
    'status' : StatusRecord,
    'objectsListPaginated' : ObjectsListRecordPaginated,
    'objectsList' : ObjectsListRecord,
    'extensionsList' : ExtensionsListRecord,
    'userGet' : UserGetRecord,
    'error' : IDL.Text,
    'message' : IDL.Text,
  });
  const RealmResponse = IDL.Record({
    'data' : RealmResponseData,
    'success' : IDL.Bool,
  });
  const ScopeListRecord = IDL.Record({ 'scopes' : IDL.Vec(IDL.Text) });
  const EnvelopeRecord = IDL.Record({
    'scope' : IDL.Text,
    'principal_id' : IDL.Text,
    'wrapped_dek' : IDL.Text,
  });
  const EnvelopeListRecord = IDL.Record({
    'envelopes' : IDL.Vec(EnvelopeRecord),
  });
  const GroupMemberRecord = IDL.Record({
    'role' : IDL.Text,
    'principal_id' : IDL.Text,
  });
  const GroupMembersRecord = IDL.Record({
    'members' : IDL.Vec(GroupMemberRecord),
  });
  const GroupRecord = IDL.Record({
    'name' : IDL.Text,
    'description' : IDL.Text,
  });
  const GroupListRecord = IDL.Record({ 'groups' : IDL.Vec(GroupRecord) });
  const CryptoResponseData = IDL.Variant({
    'scopeList' : ScopeListRecord,
    'envelope' : EnvelopeRecord,
    'error' : IDL.Text,
    'envelopeList' : EnvelopeListRecord,
    'groupMembers' : GroupMembersRecord,
    'group' : GroupRecord,
    'message' : IDL.Text,
    'groupList' : GroupListRecord,
  });
  const CryptoResponse = IDL.Record({
    'data' : CryptoResponseData,
    'success' : IDL.Bool,
  });
  const ExtensionCallArgs = IDL.Record({
    'args' : IDL.Text,
    'function_name' : IDL.Text,
    'extension_name' : IDL.Text,
  });
  const ExtensionCallResponse = IDL.Record({
    'response' : IDL.Text,
    'success' : IDL.Bool,
  });
  const Header = IDL.Tuple(IDL.Text, IDL.Text);
  const HttpRequest = IDL.Record({
    'url' : IDL.Text,
    'method' : IDL.Text,
    'body' : IDL.Vec(IDL.Nat8),
    'headers' : IDL.Vec(Header),
  });
  const StreamingToken = IDL.Record({ 'key' : IDL.Text });
  const StreamingCallbackHttpResponse = IDL.Record({
    'token' : IDL.Opt(StreamingToken),
    'body' : IDL.Vec(IDL.Nat8),
  });
  const Callback = IDL.Func(
      [StreamingToken],
      [StreamingCallbackHttpResponse],
      ['query'],
    );
  const CallbackStrategy = IDL.Record({
    'token' : StreamingToken,
    'callback' : Callback,
  });
  const StreamingStrategy = IDL.Variant({ 'Callback' : CallbackStrategy });
  const HttpResponseIncoming = IDL.Record({
    'body' : IDL.Vec(IDL.Nat8),
    'headers' : IDL.Vec(Header),
    'upgrade' : IDL.Opt(IDL.Bool),
    'streaming_strategy' : IDL.Opt(StreamingStrategy),
    'status_code' : IDL.Nat16,
  });
  const HttpHeader = IDL.Record({ 'value' : IDL.Text, 'name' : IDL.Text });
  const HttpResponse = IDL.Record({
    'status' : IDL.Nat,
    'body' : IDL.Vec(IDL.Nat8),
    'headers' : IDL.Vec(HttpHeader),
  });
  const HttpTransformArgs = IDL.Record({
    'context' : IDL.Vec(IDL.Nat8),
    'response' : HttpResponse,
  });
  return IDL.Service({
    '__get_candid_interface_tmp_hack' : IDL.Func([], [IDL.Text], ['query']),
    'change_quarter' : IDL.Func([IDL.Text], [RealmResponse], []),
    'check_verification_status' : IDL.Func([IDL.Text], [IDL.Text], []),
    'create_multi_step_scheduled_task' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Nat, IDL.Nat],
        [IDL.Text],
        [],
      ),
    'crypto_add_group_member' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'crypto_create_group' : IDL.Func(
        [IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'crypto_delete_group' : IDL.Func([IDL.Text], [CryptoResponse], []),
    'crypto_get_envelopes' : IDL.Func([IDL.Text], [CryptoResponse], ['query']),
    'crypto_get_group_members' : IDL.Func(
        [IDL.Text],
        [CryptoResponse],
        ['query'],
      ),
    'crypto_get_my_envelope' : IDL.Func(
        [IDL.Text],
        [CryptoResponse],
        ['query'],
      ),
    'crypto_get_my_scopes' : IDL.Func([], [CryptoResponse], ['query']),
    'crypto_list_groups' : IDL.Func([], [CryptoResponse], ['query']),
    'crypto_remove_group_member' : IDL.Func(
        [IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'crypto_revoke' : IDL.Func([IDL.Text, IDL.Text], [CryptoResponse], []),
    'crypto_revoke_from_group' : IDL.Func(
        [IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'crypto_share' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'crypto_share_with_group' : IDL.Func(
        [IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'crypto_store_my_envelope' : IDL.Func(
        [IDL.Text, IDL.Text],
        [CryptoResponse],
        [],
      ),
    'declare_independence' : IDL.Func([], [RealmResponse], []),
    'deregister_quarter' : IDL.Func([IDL.Text], [RealmResponse], []),
    'derive_my_vetkey' : IDL.Func([IDL.Text], [RealmResponse], []),
    'execute_code_shell' : IDL.Func([IDL.Text], [IDL.Text], []),
    'extension_async_call' : IDL.Func(
        [ExtensionCallArgs],
        [ExtensionCallResponse],
        [],
      ),
    'extension_call' : IDL.Func(
        [ExtensionCallArgs],
        [ExtensionCallResponse],
        ['query'],
      ),
    'extension_sync_call' : IDL.Func(
        [ExtensionCallArgs],
        [ExtensionCallResponse],
        [],
      ),
    'find_objects' : IDL.Func(
        [IDL.Text, IDL.Vec(IDL.Tuple(IDL.Text, IDL.Text))],
        [RealmResponse],
        ['query'],
      ),
    'get_canister_id' : IDL.Func([], [IDL.Text], ['query']),
    'get_current_application_id' : IDL.Func([IDL.Text], [IDL.Text], ['query']),
    'get_extension_frontend_info' : IDL.Func([IDL.Text], [IDL.Text], ['query']),
    'get_extensions' : IDL.Func([], [RealmResponse], ['query']),
    'get_my_invoices' : IDL.Func([], [RealmResponse], ['query']),
    'get_my_principal' : IDL.Func([], [IDL.Text], ['query']),
    'get_my_user_status' : IDL.Func([], [RealmResponse], ['query']),
    'get_my_vetkey_public_key' : IDL.Func([], [RealmResponse], []),
    'get_nft_config' : IDL.Func([], [IDL.Text], ['query']),
    'get_objects' : IDL.Func(
        [IDL.Vec(IDL.Tuple(IDL.Text, IDL.Text))],
        [RealmResponse],
        ['query'],
      ),
    'get_objects_paginated' : IDL.Func(
        [IDL.Text, IDL.Nat, IDL.Nat, IDL.Text],
        [RealmResponse],
        ['query'],
      ),
    'get_quarter_info' : IDL.Func([], [RealmResponse], ['query']),
    'get_realm_registry_info' : IDL.Func([], [IDL.Text], ['query']),
    'get_sidebar_manifests' : IDL.Func([], [IDL.Text], ['query']),
    'get_verification_link' : IDL.Func([IDL.Text], [IDL.Text], []),
    'get_zones' : IDL.Func([IDL.Nat], [IDL.Text], ['query']),
    'http_request' : IDL.Func([HttpRequest], [HttpResponseIncoming], ['query']),
    'http_transform' : IDL.Func([HttpTransformArgs], [HttpResponse], ['query']),
    'install_codex' : IDL.Func([IDL.Text], [IDL.Text], []),
    'install_codex_from_registry' : IDL.Func([IDL.Text], [IDL.Text], []),
    'install_extension' : IDL.Func([IDL.Text], [IDL.Text], []),
    'install_extension_from_registry' : IDL.Func([IDL.Text], [IDL.Text], []),
    'join_federation' : IDL.Func([IDL.Text, IDL.Bool], [RealmResponse], []),
    'join_realm' : IDL.Func([IDL.Text, IDL.Text], [RealmResponse], []),
    'list_codex_packages' : IDL.Func([], [IDL.Text], ['query']),
    'list_extensions' : IDL.Func([IDL.Text], [RealmResponse], ['query']),
    'list_runtime_extensions' : IDL.Func([], [IDL.Text], ['query']),
    'mint_land_nft_for_parcel' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Nat, IDL.Text],
        [IDL.Text],
        [],
      ),
    'refresh_invoice' : IDL.Func([IDL.Text], [IDL.Text], []),
    'register_quarter' : IDL.Func([IDL.Text, IDL.Text], [RealmResponse], []),
    'register_realm_with_registry' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Text, IDL.Text, IDL.Text],
        [IDL.Text],
        [],
      ),
    'reload_codex' : IDL.Func([IDL.Text], [IDL.Text], []),
    'reload_entity_method_overrides' : IDL.Func([], [IDL.Text], []),
    'set_application_id' : IDL.Func([IDL.Text], [IDL.Text], []),
    'set_canister_config' : IDL.Func(
        [IDL.Opt(IDL.Text), IDL.Opt(IDL.Text), IDL.Opt(IDL.Text)],
        [RealmResponse],
        [],
      ),
    'set_quarter_config' : IDL.Func([IDL.Text], [RealmResponse], []),
    'start_task_manager' : IDL.Func([], [IDL.Text], []),
    'status' : IDL.Func([], [RealmResponse], ['query']),
    'test_timer' : IDL.Func([], [IDL.Text], []),
    'uninstall_codex' : IDL.Func([IDL.Text], [IDL.Text], []),
    'uninstall_extension' : IDL.Func([IDL.Text], [IDL.Text], []),
    'update_my_private_data' : IDL.Func([IDL.Text], [RealmResponse], []),
    'update_my_public_profile' : IDL.Func(
        [IDL.Text, IDL.Text],
        [RealmResponse],
        [],
      ),
    'update_realm_config' : IDL.Func([IDL.Text], [IDL.Text], []),
  });
};
export const init = ({ IDL }) => { return []; };
