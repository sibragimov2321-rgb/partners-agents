/**
 * Giveaway control is available only to the existing manager capability.
 * There are no frontend string roles in this project: the backend returns
 * is_manager, is_superadmin and can_manage_giveaways booleans.
 */
export function canManageGiveaways(account) {
  return Boolean(account?.can_manage_giveaways ?? (account?.is_manager || account?.is_superadmin));
}
