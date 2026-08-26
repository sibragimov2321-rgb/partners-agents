import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { canManageGiveaways } from '../web/giveaway-permissions.mjs';

test('regular user cannot manage giveaways', () => {
  assert.equal(canManageGiveaways({ is_manager: false, is_superadmin: false }), false);
});

test('manager can manage giveaways', () => {
  assert.equal(canManageGiveaways({ is_manager: true, is_superadmin: false }), true);
});

test('superadmin can manage giveaways', () => {
  assert.equal(canManageGiveaways({ is_manager: false, is_superadmin: true }), true);
});

test('user sees participation card but no giveaway management button', () => {
  return readFile(new URL('../web/screens.js', import.meta.url), 'utf8').then(source => {
    assert.match(source, /data-nav="giveaway"/);
    assert.match(source, /canManage\?button\('🎁 Розыгрыши'/);
  });
});

test('manager and superadmin see the giveaway management button', () => {
  return readFile(new URL('../web/screens.js', import.meta.url), 'utf8').then(source => {
    assert.match(source, /const c=text\(lang\).*canManage=canManageGiveaways\(account\)/);
    assert.match(source, /canManage\?button\('🎁 Розыгрыши'/);
  });
});

test('empty manager dashboard always offers creation of the first giveaway', () => {
  return readFile(new URL('../web/giveaways.js', import.meta.url), 'utf8').then(source => {
    assert.match(source, /Пока нет созданных розыгрышей/);
    assert.match(source, /➕ Создать розыгрыш/);
    assert.match(source, /\$\{button\('➕ Создать розыгрыш'.*\)\}\$\{list\}/);
  });
});

test('hyphenated giveaway navigation resolves to an internal manager route', () => {
  return readFile(new URL('../web/app.js', import.meta.url), 'utf8').then(source => {
    assert.match(source, /function go\(view\)\{state\.view=String\(view\)\.replaceAll\('-','_'\)/);
    assert.match(source, /target\.dataset\.nav==='manager-giveaways'/);
  });
});
