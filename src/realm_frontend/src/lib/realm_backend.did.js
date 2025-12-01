type ExtensionCallArgs = record {
  args : text;
  function_name : text;
  extension_name : text;
};
type ExtensionCallResponse = record { response : text; success : bool };
type ExtensionsListRecord = record { extensions : vec text };
type HttpHeader = record { value : text; name : text };
type HttpResponse = record {
  status : nat;
  body : blob;
  headers : vec HttpHeader;
};
type HttpTransformArgs = record { context : blob; response : HttpResponse };
type ObjectsListRecord = record { objects : vec text };
type ObjectsListRecordPaginated = record {
  pagination : PaginationInfo;
  objects : vec text;
};
type PaginationInfo = record {
  page_size : int;
  total_pages : int;
  total_items_count : int;
  page_num : int;
};
type RealmResponse = record { data : RealmResponseData; success : bool };
type RealmResponseData = variant {
  status : StatusRecord;
  objectsListPaginated : ObjectsListRecordPaginated;
  objectsList : ObjectsListRecord;
  extensionsList : ExtensionsListRecord;
  userGet : UserGetRecord;
  error : text;
  message : text;
};
type StatusRecord = record {
  status : text;
  demo_mode : bool;
  transfers_count : nat;
  codexes_count : nat;
  proposals_count : nat;
  realms_count : nat;
  version : text;
  extensions : vec text;
  disputes_count : nat;
  commit : text;
  instruments_count : nat;
  organizations_count : nat;
  mandates_count : nat;
  tasks_count : nat;
  votes_count : nat;
  licenses_count : nat;
  users_count : nat;
  trades_count : nat;
};
type UserGetRecord = record {
  "principal" : principal;
  profile_picture_url : text;
  profiles : vec text;
};
service : () -> {
  check_verification_status : (text) -> (text);
  create_multi_step_scheduled_task : (text, text, nat, nat) -> (text);
  create_scheduled_task : (text, text, nat, nat) -> (text);
  download_file : (text, text, opt text, opt text) -> (text);
  download_file_from_url : (text) -> (record { bool; text });
  execute_code : (text) -> (text);
  execute_code_shell : (text) -> (text);
  extension_async_call : (ExtensionCallArgs) -> (ExtensionCallResponse);
  extension_sync_call : (ExtensionCallArgs) -> (ExtensionCallResponse);
  get_canister_id : () -> (text) query;
  get_current_application_id : (text) -> (text) query;
  get_extensions : () -> (RealmResponse) query;
  get_my_principal : () -> (text) query;
  get_my_user_status : () -> (RealmResponse) query;
  get_objects : (vec record { text; text }) -> (RealmResponse) query;
  get_objects_paginated : (text, nat, nat, text) -> (RealmResponse) query;
  get_realm_registry_info : () -> (text) query;
  get_task_logs : (text, nat) -> (text) query;
  get_task_logs_by_name : (text, nat, nat) -> (text) query;
  get_verification_link : (text) -> (text);
  http_transform : (HttpTransformArgs) -> (HttpResponse) query;
  initialize : () -> ();
  join_realm : (text) -> (RealmResponse);
  list_extensions : (text) -> (RealmResponse) query;
  register_realm_with_registry : (text, text, text, text) -> (text);
  reload_entity_method_overrides : () -> (text);
  set_application_id : (text) -> (text);
  status : () -> (RealmResponse) query;
  stop_task : (text) -> (text);
  test_mixed_sync_async_task : () -> ();
  update_my_profile_picture : (text) -> (RealmResponse);
}
