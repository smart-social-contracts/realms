/**
 * Decode UserGetRecord bytes with the same @dfinity/candid IDL the SPA uses.
 * Used by test_user_departments.py to prove join_realm's empty departments
 * vec {} survives JS actor decode.
 */
import { IDL } from '@dfinity/candid';
import { Principal } from '@dfinity/principal';

const UserGetRecord = IDL.Record({
	assigned_quarter: IDL.Text,
	principal: IDL.Principal,
	private_data: IDL.Text,
	nickname: IDL.Text,
	profiles: IDL.Vec(IDL.Text),
	departments: IDL.Vec(IDL.Text),
	avatar: IDL.Text
});

const hex = process.argv[2];
if (!hex) {
	console.error('usage: decode_user_get_record.mjs <hex>');
	process.exit(2);
}
const bytes = Uint8Array.from(Buffer.from(hex, 'hex'));
try {
	const [value] = IDL.decode([UserGetRecord], bytes);
	const departments = value.departments;
	if (!Array.isArray(departments)) {
		throw new Error('departments is not a vec');
	}
	console.log(
		JSON.stringify({
			ok: true,
			departments,
			keys: Object.keys(value).sort(),
			principal: Principal.from(value.principal).toText()
		})
	);
} catch (e) {
	console.log(JSON.stringify({ ok: false, error: e.message || String(e) }));
	process.exit(1);
}
