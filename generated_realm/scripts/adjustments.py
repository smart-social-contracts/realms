from kybra import ic
from ggg import Realm, Treasury, UserProfile, User, Codex

ic.print("Setting treasury vault principal...")

vault_principal_id = "uzt4z-lp777-77774-qaabq-cai"
treasury = Treasury()
treasury.vault_principal_id = vault_principal_id


ic.print("len(Realm.instances()) = %d" % len(Realm.instances()))
ic.print("len(Treasury.instances()) = %d" % len(Treasury.instances()))
ic.print("len(UserProfile.instances()) = %d" % len(UserProfile.instances()))
ic.print("len(User.instances()) = %d" % len(User.instances()))
ic.print("len(Codex.instances()) = %d" % len(Codex.instances()))

for codex in Codex.instances():
    ic.print(f"{codex.name}: {len(codex.code)}")