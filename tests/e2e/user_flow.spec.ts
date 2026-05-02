import { test, expect } from '@playwright/test';

test('User lifecycle: signup, login, analyze, logout, delete', async ({ page }) => {
  const username = `testuser_${Date.now()}`;
  const password = 'password123';

  // 1. Signup
  await page.goto('/');
  await page.click('text=ログイン / 新規登録');
  await page.click('text=新規登録');
  await page.locator('input[autoComplete="username"]').fill(username);
  await page.locator('input[autoComplete="new-password"]').fill(password);
  
  // Listen for signup alert
  page.once('dialog', dialog => dialog.accept());
  await page.click('button:has-text("アカウント作成")');

  // 2. Login
  // Signup redirects to login mode automatically in AuthModal.tsx
  await page.locator('input[autoComplete="username"]').fill(username);
  await page.locator('input[autoComplete="current-password"]').fill(password);
  await page.click('button:has-text("ログイン")');

  // Verify login success
  await expect(page.locator('.user-name')).toContainText(username);

  // 3. Analyze (and save history)
  await page.fill('input[placeholder="例: Sony, 7203, AAPL"]', '7203');
  await page.click('button:has-text("自動判定を開始")');
  
  // Wait for result signal to appear
  await expect(page.locator('.signal-text')).toBeVisible({ timeout: 20000 });
  
  // 4. Check History
  await page.click('button[aria-label="メニュー"]');
  await page.click('text=履歴を見る');
  await expect(page.locator('.history-list')).toContainText('7203', { timeout: 10000 });

  // 5. Logout
  await page.click('button[aria-label="メニュー"]');
  await page.click('text=ログアウト');
  await expect(page.locator('text=ログイン / 新規登録')).toBeVisible();

  // 6. Login again
  await page.click('text=ログイン / 新規登録');
  await page.locator('input[autoComplete="username"]').fill(username);
  await page.locator('input[autoComplete="current-password"]').fill(password);
  await page.click('button:has-text("ログイン")');
  await expect(page.locator('.user-name')).toContainText(username);

  // 7. Withdraw (Delete account)
  await page.click('button[aria-label="メニュー"]');
  
  // Listen for confirmation dialog
  page.once('dialog', dialog => {
    expect(dialog.message()).toContain('本当に退会しますか？');
    return dialog.accept();
  });
  
  // Listen for success alert
  page.once('dialog', dialog => {
    expect(dialog.message()).toContain('退会処理が完了しました');
    return dialog.accept();
  });
  
  await page.click('text=退会する');
  
  // Verify redirected/logged out
  await expect(page.locator('text=ログイン / 新規登録')).toBeVisible();

  // 8. Verify login fails after withdrawal
  await page.click('text=ログイン / 新規登録');
  await page.locator('input[autoComplete="username"]').fill(username);
  await page.locator('input[autoComplete="current-password"]').fill(password);
  await page.click('button:has-text("ログイン")');
  await expect(page.locator('.alert-box.danger')).toBeVisible();
  await expect(page.locator('.alert-box.danger')).toContainText('ユーザー名またはパスワードが正しくありません');
});
