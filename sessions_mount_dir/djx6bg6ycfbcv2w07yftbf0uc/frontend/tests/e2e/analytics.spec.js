const { test, expect } = require('@playwright/test');

test.describe('商家端数据统计', () => {
  test.beforeEach(async ({ page }) => {
    // 模拟商家登录
    await page.goto('/login');
    await page.fill('[data-testid=username]', 'merchant_test');
    await page.fill('[data-testid=password]', 'test123456');
    await page.click('[data-testid=login-button]');
    await page.waitForURL('/dashboard');
    
    // 导航到数据统计页面
    await page.click('[data-testid=analytics-menu]');
    await page.waitForURL('/merchant/analytics');
  });

  test('应该正确显示数据统计页面', async ({ page }) => {
    // 验证页面标题
    await expect(page.locator('h1')).toContainText('数据统计');
    
    // 验证日期选择器存在
    await expect(page.locator('.el-date-editor')).toBeVisible();
    
    // 验证汇总卡片存在
    await expect(page.locator('.summary-cards')).toBeVisible();
    await expect(page.locator('.summary-card')).toHaveCount(4);
  });

  test('应该正确显示汇总卡片数据', async ({ page }) => {
    // 等待数据加载
    await page.waitForSelector('.summary-card:not(.el-loading-mask)');
    
    // 验证每个卡片的内容
    const cards = page.locator('.summary-card');
    
    // 验证第一个卡片（总预约量）
    await expect(cards.nth(0).locator('.card-title')).toContainText('总预约量');
    await expect(cards.nth(0).locator('.card-value')).toBeVisible();
    await expect(cards.nth(0).locator('.card-trend')).toBeVisible();
    
    // 验证第二个卡片（会员总数）
    await expect(cards.nth(1).locator('.card-title')).toContainText('会员总数');
    await expect(cards.nth(1).locator('.card-value')).toBeVisible();
    
    // 验证第三个卡片（总收入）
    await expect(cards.nth(2).locator('.card-title')).toContainText('总收入');
    await expect(cards.nth(2).locator('.card-value')).toBeVisible();
    
    // 验证第四个卡片（活跃课程）
    await expect(cards.nth(3).locator('.card-title')).toContainText('活跃课程');
    await expect(cards.nth(3).locator('.card-value')).toBeVisible();
  });

  test('应该正确切换课程预约量时间周期', async ({ page }) => {
    // 等待图表加载
    await page.waitForSelector('.booking-chart');
    
    // 点击周视图
    await page.click('[data-testid=booking-week-btn]');
    await expect(page.locator('[data-testid=booking-week-btn]')).toHaveClass(/primary/);
    
    // 点击月视图
    await page.click('[data-testid=booking-month-btn]');
    await expect(page.locator('[data-testid=booking-month-btn]')).toHaveClass(/primary/);
  });

  test('应该正确显示会员增长趋势图表', async ({ page }) => {
    // 等待图表加载
    await page.waitForSelector('.member-chart');
    
    // 验证图表容器存在
    await expect(page.locator('.member-chart')).toBeVisible();
    
    // 验证图表标题
    await expect(page.locator('.chart-card').filter({ hasText: '会员增长趋势' })).toBeVisible();
  });

  test('应该正确显示热门课程排行', async ({ page }) => {
    // 等待图表加载
    await page.waitForSelector('.course-ranking-chart');
    
    // 验证图表容器存在
    await expect(page.locator('.course-ranking-chart')).toBeVisible();
    
    // 验证图表标题
    await expect(page.locator('.chart-card').filter({ hasText: '热门课程排行' })).toBeVisible();
  });

  test('应该正确显示收入统计图表', async ({ page }) => {
    // 等待图表加载
    await page.waitForSelector('.revenue-chart');
    
    // 验证图表容器存在
    await expect(page.locator('.revenue-chart')).toBeVisible();
    
    // 验证图表标题
    await expect(page.locator('.chart-card').filter({ hasText: '收入统计' })).toBeVisible();
  });

  test('应该正确处理日期范围选择', async ({ page }) => {
    // 获取日期选择器
    const datePicker = page.locator('.el-date-editor');
    
    // 点击打开日期选择器
    await datePicker.click();
    
    // 验证日期面板打开
    await expect(page.locator('.el-picker-panel')).toBeVisible();
    
    // 选择快捷选项（最近7天）
    await page.click('[data-testid=shortcut-7days]');
    
    // 验证日期范围已更新
    await expect(datePicker.locator('input').first()).toHaveValue(/\d{4}-\d{2}-\d{2}/);
    await expect(datePicker.locator('input').last()).toHaveValue(/\d{4}-\d{2}-\d{2}/);
    
    // 验证数据重新加载
    await page.waitForSelector('.summary-card:not(.el-loading-mask)');
  });

  test('应该正确处理数据导出功能', async ({ page }) => {
    // 等待导出按钮加载
    await page.waitForSelector('[data-testid=export-button]');
    
    // 点击导出按钮
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid=export-button]');
    const download = await downloadPromise;
    
    // 验证下载文件名
    expect(download.suggestedFilename()).toMatch(/analytics_.*\.xlsx/);
  });

  test('应该正确处理数据刷新', async ({ page }) => {
    // 等待初始数据加载
    await page.waitForSelector('.summary-card:not(.el-loading-mask)');
    
    // 点击刷新按钮
    await page.click('[data-testid=refresh-button]');
    
    // 验证加载状态
    await expect(page.locator('.summary-cards').locator('.el-loading-mask')).toBeVisible();
    
    // 验证数据重新加载完成
    await page.waitForSelector('.summary-card:not(.el-loading-mask)');
  });

  test('应该正确响应式布局', async ({ page }) => {
    // 测试桌面视图
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator('.charts-container .el-col')).toHaveCount(4);
    
    // 测试平板视图
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('.charts-container .el-col')).toHaveCount(4);
    
    // 测试手机视图
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('.charts-container .el-col')).toHaveCount(4);
  });

  test('应该正确处理错误状态', async ({ page }) => {
    // 模拟API错误
    await page.route('**/api/analytics/summary', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });
    
    // 刷新页面
    await page.reload();
    
    // 验证错误提示
    await expect(page.locator('.el-message--error')).toBeVisible();
    await expect(page.locator('.el-message--error')).toContainText('数据加载失败');
  });

  test('应该正确处理空数据状态', async ({ page }) => {
    // 模拟空数据响应
    await page.route('**/api/analytics/summary', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          totalBookings: 0,
          totalMembers: 0,
          totalRevenue: 0,
          activeCourses: 0
        })
      });
    });
    
    // 刷新页面
    await page.reload();
    
    // 验证空数据显示
    await expect(page.locator('.summary-card').nth(0).locator('.card-value')).toContainText('0');
    await expect(page.locator('.summary-card').nth(1).locator('.card-value')).toContainText('0');
  });
});