export const idlFactory = ({ IDL }) => {
  return IDL.Service({
    '__get_candid_interface_tmp_hack' : IDL.Func([], [IDL.Text], ['query']),
    'cancel_deploy' : IDL.Func([IDL.Text], [IDL.Text], []),
    'debug_resume_deploys' : IDL.Func([IDL.Text], [IDL.Text], []),
    'debug_run_one_step' : IDL.Func([IDL.Text], [IDL.Text], []),
    'deploy_frontend' : IDL.Func([IDL.Text], [IDL.Text], []),
    'deploy_realm' : IDL.Func([IDL.Text], [IDL.Text], []),
    'execute_code_shell' : IDL.Func([IDL.Text], [IDL.Text], []),
    'fetch_module_hash' : IDL.Func([IDL.Text], [IDL.Text], []),
    'get_deploy_status' : IDL.Func([IDL.Text], [IDL.Text], ['query']),
    'health' : IDL.Func([], [IDL.Text], ['query']),
    'info' : IDL.Func([], [IDL.Text], ['query']),
    'install_realm_backend' : IDL.Func([IDL.Text], [IDL.Text], []),
    'list_deploys' : IDL.Func([], [IDL.Text], ['query']),
  });
};
export const init = ({ IDL }) => { return []; };
