/**
 * Crypto envelope management for basilisk OS integration.
 *
 * Provides functions to store/retrieve key envelopes (wrapped DEKs) and
 * manage crypto groups via the realm backend canister.
 *
 * Envelopes use the format: `env:v=2:k=<wrapped-dek-hex>`
 * Ciphertext uses the format: `enc:v=2:iv=<hex>:d=<hex>`
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Envelope {
	scope: string;
	principalId: string;
	wrappedDek: string;
}

export interface CryptoGroup {
	name: string;
	description: string;
}

export interface GroupMember {
	principalId: string;
	role: string;
}

// ---------------------------------------------------------------------------
// Format helpers (mirror basilisk.os.crypto Python helpers)
// ---------------------------------------------------------------------------

/** Encode a wrapped DEK into the standard envelope format. */
export function encodeEnvelope(wrappedDekHex: string): string {
	return `env:v=2:k=${wrappedDekHex}`;
}

/** Decode an envelope string to extract the wrapped DEK hex. */
export function decodeEnvelope(envelope: string): string {
	if (!envelope || !envelope.startsWith('env:v=2:k=')) {
		throw new Error(`Invalid envelope format: ${envelope}`);
	}
	return envelope.slice('env:v=2:k='.length);
}

/** Check if a string is in encrypted format. */
export function isEncrypted(value: string): boolean {
	return !!value && value.startsWith('enc:v=2:');
}

/** Check if a string is an envelope. */
export function isEnvelope(value: string): boolean {
	return !!value && value.startsWith('env:v=2:');
}

// ---------------------------------------------------------------------------
// Envelope CRUD (via backend canister)
// ---------------------------------------------------------------------------

/**
 * Store (or update) the caller's wrapped DEK envelope for a scope.
 *
 * @param backend Authenticated canister actor.
 * @param scope   Scope identifier (e.g. `"user:<principal>:private"`).
 * @param wrappedDek  The wrapped DEK hex to store.
 */
export async function storeMyEnvelope(
	backend: any,
	scope: string,
	wrappedDek: string
): Promise<Envelope> {
	const resp = await backend.crypto_store_my_envelope(scope, wrappedDek);
	if (!resp.success) {
		throw new Error(`Failed to store envelope: ${resp.data?.error || 'unknown'}`);
	}
	const env = resp.data.envelope;
	return {
		scope: env.scope,
		principalId: env.principal_id,
		wrappedDek: env.wrapped_dek
	};
}

/**
 * Retrieve the caller's envelope for a scope.
 *
 * @returns The envelope, or `null` if none exists.
 */
export async function getMyEnvelope(backend: any, scope: string): Promise<Envelope | null> {
	const resp = await backend.crypto_get_my_envelope(scope);
	if (!resp.success) return null;
	const env = resp.data.envelope;
	return {
		scope: env.scope,
		principalId: env.principal_id,
		wrappedDek: env.wrapped_dek
	};
}

/** List all scopes the caller has access to. */
export async function getMyScopes(backend: any): Promise<string[]> {
	const resp = await backend.crypto_get_my_scopes();
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to list scopes');
	return resp.data.scopeList.scopes;
}

// ---------------------------------------------------------------------------
// Admin: sharing & revocation
// ---------------------------------------------------------------------------

/** List all envelopes for a scope (admin only). */
export async function getEnvelopes(backend: any, scope: string): Promise<Envelope[]> {
	const resp = await backend.crypto_get_envelopes(scope);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to list envelopes');
	return resp.data.envelopeList.envelopes.map((e: any) => ({
		scope: e.scope,
		principalId: e.principal_id,
		wrappedDek: e.wrapped_dek
	}));
}

/** Share access to a scope with another principal (admin only). */
export async function shareWithPrincipal(
	backend: any,
	scope: string,
	targetPrincipal: string,
	wrappedDek: string
): Promise<void> {
	const resp = await backend.crypto_share(scope, targetPrincipal, wrappedDek);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to share');
}

/** Revoke a principal's access to a scope (admin only). */
export async function revokePrincipal(
	backend: any,
	scope: string,
	targetPrincipal: string
): Promise<void> {
	const resp = await backend.crypto_revoke(scope, targetPrincipal);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to revoke');
}

// ---------------------------------------------------------------------------
// Group management
// ---------------------------------------------------------------------------

/** Create a new crypto group (admin only). */
export async function createGroup(
	backend: any,
	name: string,
	description: string = ''
): Promise<CryptoGroup> {
	const resp = await backend.crypto_create_group(name, description);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to create group');
	return { name: resp.data.group.name, description: resp.data.group.description };
}

/** Delete a crypto group (admin only). */
export async function deleteGroup(backend: any, name: string): Promise<void> {
	const resp = await backend.crypto_delete_group(name);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to delete group');
}

/** Add a principal to a group (admin only). */
export async function addGroupMember(
	backend: any,
	groupName: string,
	principal: string,
	role: string = 'member'
): Promise<void> {
	const resp = await backend.crypto_add_group_member(groupName, principal, role);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to add member');
}

/** Remove a principal from a group (admin only). */
export async function removeGroupMember(
	backend: any,
	groupName: string,
	principal: string
): Promise<void> {
	const resp = await backend.crypto_remove_group_member(groupName, principal);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to remove member');
}

/** List all crypto groups. */
export async function listGroups(backend: any): Promise<CryptoGroup[]> {
	const resp = await backend.crypto_list_groups();
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to list groups');
	return resp.data.groupList.groups.map((g: any) => ({
		name: g.name,
		description: g.description
	}));
}

/** List members of a crypto group. */
export async function listGroupMembers(backend: any, groupName: string): Promise<GroupMember[]> {
	const resp = await backend.crypto_get_group_members(groupName);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to list members');
	return resp.data.groupMembers.members.map((m: any) => ({
		principalId: m.principal_id,
		role: m.role
	}));
}

/** Share access to a scope with all members of a group (admin only). */
export async function shareWithGroup(
	backend: any,
	scope: string,
	groupName: string
): Promise<void> {
	const resp = await backend.crypto_share_with_group(scope, groupName);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to share with group');
}

/** Revoke all group members' access to a scope (admin only). */
export async function revokeGroup(
	backend: any,
	scope: string,
	groupName: string
): Promise<void> {
	const resp = await backend.crypto_revoke_from_group(scope, groupName);
	if (!resp.success) throw new Error(resp.data?.error || 'Failed to revoke group');
}
