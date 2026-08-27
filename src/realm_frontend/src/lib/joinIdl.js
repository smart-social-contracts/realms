/**
 * Join-only IDL: UserGetRecord.departments is Reserved.
 *
 * The generated realm_backend IDL requires ``departments: vec text``.
 * @dfinity/candid then throws ``Cannot find required field departments``
 * when the wire record omits the field (old quarter WASM, or a constructor
 * that stored home_quarter instead of the DID keys).
 *
 * Reserved accepts the field when present (any type) and when missing.
 * Join does not need the department list — loadUserProfiles reads it later.
 */
import { IDL } from '@dfinity/candid';

export function joinIdlFactory({ IDL: FactoryIDL } = { IDL }) {
	const I = FactoryIDL || IDL;
	const UserGetRecord = I.Record({
		assigned_quarter: I.Text,
		principal: I.Principal,
		private_data: I.Text,
		nickname: I.Text,
		profiles: I.Vec(I.Text),
		departments: I.Reserved,
		avatar: I.Text
	});
	const RealmResponseData = I.Variant({
		status: I.Reserved,
		objectsListPaginated: I.Reserved,
		objectsList: I.Reserved,
		extensionsList: I.Reserved,
		userGet: UserGetRecord,
		error: I.Text,
		message: I.Text
	});
	const RealmResponse = I.Record({
		data: RealmResponseData,
		success: I.Bool
	});
	return I.Service({
		join_realm: I.Func([I.Text, I.Text, I.Text], [RealmResponse], [])
	});
}
