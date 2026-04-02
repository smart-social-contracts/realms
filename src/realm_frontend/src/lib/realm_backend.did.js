export const idlFactory = ({ IDL }) => {
  const ExtensionCallArgs = IDL.Record({
    'args' : IDL.Text,
    'function_name' : IDL.Text,
    'extension_name' : IDL.Text,
  });
  const ExtensionCallResponse = IDL.Record({
    'response' : IDL.Text,
    'success' : IDL.Bool,
  });
  const ExtensionsListRecord = IDL.Record({
    'extensions' : IDL.Vec(IDL.Text),
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
  const ObjectsListRecord = IDL.Record({
    'objects' : IDL.Vec(IDL.Text),
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
  const QuarterInfoRecord = IDL.Record({
    'name' : IDL.Text,
    'canister_id' : IDL.Text,
    'population' : IDL.Nat,
    'status' : IDL.Text,
  });
  const CanisterInfo = IDL.Record({
    'canister_id' : IDL.Text,
    'canister_type' : IDL.Text,
  });
  const StatusRecord = IDL.Record({
    'status' : IDL.Text,
    'test_mode' : IDL.Bool,
    'transfers_count' : IDL.Nat,
    'codexes_count' : IDL.Nat,
    'proposals_count' : IDL.Nat,
    'realms_count' : IDL.Nat,
    'version' : IDL.Text,
    'extensions' : IDL.Vec(IDL.Text),
    'disputes_count' : IDL.Nat,
    'commit' : IDL.Text,
    'commit_datetime' : IDL.Text,
    'instruments_count' : IDL.Nat,
    'organizations_count' : IDL.Nat,
    'mandates_count' : IDL.Nat,
    'tasks_count' : IDL.Nat,
    'votes_count' : IDL.Nat,
    'licenses_count' : IDL.Nat,
    'users_count' : IDL.Nat,
    'trades_count' : IDL.Nat,
    'user_profiles_count' : IDL.Nat,
    'canisters' : IDL.Vec(CanisterInfo),
    'registries' : IDL.Vec(CanisterInfo),
    'dependencies' : IDL.Vec(IDL.Text),
    'python_version' : IDL.Text,
    'quarters' : IDL.Vec(QuarterInfoRecord),
    'is_quarter' : IDL.Bool,
    'parent_realm_canister_id' : IDL.Text,
    'realm_name' : IDL.Text,
    'realm_logo' : IDL.Text,
    'realm_description' : IDL.Text,
    'realm_welcome_image' : IDL.Text,
    'realm_welcome_message' : IDL.Text,
    'accounting_currency' : IDL.Text,
    'accounting_currency_decimals' : IDL.Nat,
  });
  const UserGetRecord = IDL.Record({
    'principal' : IDL.Principal,
    'nickname' : IDL.Text,
    'avatar' : IDL.Text,
    'private_data' : IDL.Text,
    'profiles' : IDL.Vec(IDL.Text),
    'assigned_quarter' : IDL.Text,
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
  return IDL.Service({
    'check_verification_status' : IDL.Func([IDL.Text], [IDL.Text], []),
    'create_multi_step_scheduled_task' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Nat, IDL.Nat],
        [IDL.Text],
        [],
      ),
    'create_scheduled_task' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Nat, IDL.Nat],
        [IDL.Text],
        [],
      ),
    'download_file' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Opt(IDL.Text), IDL.Opt(IDL.Text)],
        [IDL.Text],
        [],
      ),
    'download_file_from_url' : IDL.Func(
        [IDL.Text],
        [IDL.Tuple(IDL.Bool, IDL.Text)],
        [],
      ),
    'execute_code' : IDL.Func([IDL.Text], [IDL.Text], []),
    'execute_code_shell' : IDL.Func([IDL.Text], [IDL.Text], []),
    'extension_async_call' : IDL.Func(
        [ExtensionCallArgs],
        [ExtensionCallResponse],
        [],
      ),
    'extension_sync_call' : IDL.Func(
        [ExtensionCallArgs],
        [ExtensionCallResponse],
        [],
      ),
    'get_canister_id' : IDL.Func([], [IDL.Text], ['query']),
    'get_current_application_id' : IDL.Func(
        [IDL.Text],
        [IDL.Text],
        ['query'],
      ),
    'get_extensions' : IDL.Func([], [RealmResponse], ['query']),
    'get_quarter_info' : IDL.Func([], [RealmResponse], ['query']),
    'get_my_principal' : IDL.Func([], [IDL.Text], ['query']),
    'get_my_user_status' : IDL.Func([], [RealmResponse], ['query']),
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
    'get_realm_registry_info' : IDL.Func([], [IDL.Text], ['query']),
    'get_task_logs' : IDL.Func(
        [IDL.Text, IDL.Nat],
        [IDL.Text],
        ['query'],
      ),
    'get_task_logs_by_name' : IDL.Func(
        [IDL.Text, IDL.Nat, IDL.Nat],
        [IDL.Text],
        ['query'],
      ),
    'get_verification_link' : IDL.Func([IDL.Text], [IDL.Text], []),
    'http_transform' : IDL.Func(
        [HttpTransformArgs],
        [HttpResponse],
        ['query'],
      ),
    'initialize' : IDL.Func([], [], []),
    'change_quarter' : IDL.Func([IDL.Text], [RealmResponse], []),
    'join_realm' : IDL.Func([IDL.Text, IDL.Text], [RealmResponse], []),
    'list_extensions' : IDL.Func([IDL.Text], [RealmResponse], ['query']),
    'register_realm_with_registry' : IDL.Func(
        [IDL.Text, IDL.Text, IDL.Text, IDL.Text],
        [IDL.Text],
        [],
      ),
    'refresh_invoice' : IDL.Func([IDL.Text], [IDL.Text], []),
    'reload_entity_method_overrides' : IDL.Func([], [IDL.Text], []),
    'register_quarter' : IDL.Func(
        [IDL.Text, IDL.Text],
        [RealmResponse],
        [],
      ),
    'deregister_quarter' : IDL.Func([IDL.Text], [RealmResponse], []),
    'set_quarter_config' : IDL.Func([IDL.Text], [RealmResponse], []),
    'set_application_id' : IDL.Func([IDL.Text], [IDL.Text], []),
    'status' : IDL.Func([], [RealmResponse], ['query']),
    'stop_task' : IDL.Func([IDL.Text], [IDL.Text], []),
    'test_mixed_sync_async_task' : IDL.Func([], [], []),
    'update_my_public_profile' : IDL.Func(
        [IDL.Text, IDL.Text],
        [RealmResponse],
        [],
      ),
    'update_my_private_data' : IDL.Func([IDL.Text], [RealmResponse], []),
    'get_my_vetkey_public_key' : IDL.Func([], [RealmResponse], []),
    'derive_my_vetkey' : IDL.Func([IDL.Text], [RealmResponse], []),
  });
};
export const init = ({ IDL }) => { return []; };
