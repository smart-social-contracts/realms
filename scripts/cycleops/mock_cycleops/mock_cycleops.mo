/// Mock CycleOps canister for local E2E testing.
///
/// Implements the subset of the real CycleOps API used by the deployment
/// worker: createCanister and manualTopup.  Deploy to a local dfx replica
/// so the deployment worker exercises the same code path regardless of
/// network.

import Error "mo:base/Error";

persistent actor MockCycleOps {

  type CreateCanisterResult = {
    canister_id : Principal;
  };

  type CanisterSettings = {
    controllers : ?[Principal];
    compute_allocation : ?Nat;
    memory_allocation : ?Nat;
    freezing_threshold : ?Nat;
  };

  transient let ic : actor {
    create_canister : ({ settings : ?CanisterSettings }) -> async CreateCanisterResult;
    update_settings : ({ canister_id : Principal; settings : CanisterSettings }) -> async ();
    deposit_cycles : ({ canister_id : Principal }) -> async ();
  } = actor "aaaaa-aa";

  type TopupRule = {
    threshold : Nat;
    method : { #by_amount : Nat; #to_balance : Nat };
  };

  type SubnetSelection = {
    #Filter : { subnet_type : ?Text };
    #Subnet : { subnet : Principal };
  };

  type ManualTopupType = {
    #cycles : Nat;
    #icp : { e8s : Nat64 };
  };

  public shared func createCanister(args : {
    asTeamPrincipal : ?Principal;
    controllers : [Principal];
    name : ?Text;
    subnetSelection : ?SubnetSelection;
    topupRule : ?TopupRule;
    withStartingCyclesBalance : Nat;
  }) : async { #ok : Principal; #err : Text } {
    try {
      let result = await (with cycles = args.withStartingCyclesBalance) ic.create_canister({
        settings = ?{
          controllers = ?args.controllers;
          compute_allocation = null;
          memory_allocation = null;
          freezing_threshold = null;
        };
      });
      #ok(result.canister_id);
    } catch (e) {
      #err(Error.message(e));
    };
  };

  public shared func manualTopup(args : {
    asTeamPrincipal : ?Principal;
    canisterId : Principal;
    topupAmount : ManualTopupType;
  }) : async { #ok; #err : Text } {
    switch (args.topupAmount) {
      case (#cycles(amount)) {
        try {
          await (with cycles = amount) ic.deposit_cycles({ canister_id = args.canisterId });
          #ok;
        } catch (e) {
          #err(Error.message(e));
        };
      };
      case (#icp(_)) {
        #err("ICP topup not supported in mock");
      };
    };
  };
};
