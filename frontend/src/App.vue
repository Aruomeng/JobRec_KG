<template>
  <a-config-provider :locale="zhCN">
    <a-layout class="app-layout">
      <!-- 顶部导航（仅主页面显示，登录页不显示） -->
      <a-layout-header v-if="!isLoginPage" :class="['app-header', `app-header-${currentRole}`]">
        <div class="logo">
          <RocketOutlined class="logo-icon" />
          <span class="logo-text">{{ currentTitle }}</span>
        </div>
        <div class="header-right" v-if="isLoggedIn">
          <a-tag color="rgba(255,255,255,0.2)" style="border: 1px solid rgba(255,255,255,0.3); color: white;">
            <IdcardOutlined /> {{ userInfo?.student_id || userInfo?.user_id || '-' }}
          </a-tag>
          <span class="user-name">{{ userInfo?.name || userInfo?.display_name || '用户' }}</span>
          <a-button type="link" @click="showProfileModal" class="header-btn">
            编辑资料
          </a-button>
          <a-divider type="vertical" style="background: rgba(255,255,255,0.3);" />
          <a-button type="link" @click="handleLogout" class="header-btn logout-btn">
            退出登录
          </a-button>
        </div>
      </a-layout-header>

      <!-- 主体内容 -->
      <a-layout-content :class="['app-content', { 'no-header': isLoginPage }]">
        <router-view v-slot="{ Component }">
          <keep-alive :include="['StudentDashboard', 'TalentScout', 'GapAnalysis']">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </a-layout-content>

      <!-- 页脚（登录页和企业中心不显示） -->
      <a-layout-footer v-if="!isLoginPage && !isEnterpriseCenter" class="app-footer">
        智途AI就业推荐系统 ©2026 基于知识图谱与GraphSAGE
      </a-layout-footer>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Modal } from 'ant-design-vue'
import { ExclamationCircleOutlined, RocketOutlined, IdcardOutlined } from '@ant-design/icons-vue'
import { createVNode } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 判断是否是登录页
const isLoginPage = computed(() => route.path.startsWith('/login'))

// 判断是否是企业中心页
const isEnterpriseCenter = computed(() => route.path === '/enterprise/center')

// 判断是否已登录 (使用 store)
const isLoggedIn = computed(() => userStore.isLoggedIn)

// 用户信息 (使用 store)
const userInfo = computed(() => userStore.userInfo || {})

// 当前页面标题
const currentTitle = computed(() => {
  if (route.path.startsWith('/student')) return '智途AI · 学生就业服务'
  if (route.path.startsWith('/enterprise')) return '智途AI · 企业人才招聘'
  if (route.path.startsWith('/university')) return '智途AI · 高校就业管理'
  return '智途AI就业推荐系统'
})

// 当前角色(用于主题色)
const currentRole = computed(() => {
  if (route.path.startsWith('/student')) return 'student'
  if (route.path.startsWith('/enterprise')) return 'enterprise'
  if (route.path.startsWith('/university')) return 'university'
  return 'student'
})

// 编辑资料 - 根据角色跳转
const showProfileModal = () => {
  // 企业端跳转到企业中心
  if (currentRole.value === 'enterprise') {
    router.push('/enterprise/center')
    return
  }
  // 高校端(暂无个人中心，留作扩展)
  if (currentRole.value === 'university') {
    // router.push('/university/center')
    window.dispatchEvent(new CustomEvent('open-profile-modal'))
    return
  }
  // 学生端触发弹窗
  window.dispatchEvent(new CustomEvent('open-profile-modal'))
}

// 退出登录 - 带确认对话框
const handleLogout = () => {
  Modal.confirm({
    title: '确认退出',
    icon: createVNode(ExclamationCircleOutlined),
    content: '确定要退出登录吗？',
    okText: '确定退出',
    cancelText: '取消',
    okType: 'danger',
    centered: true,
    onOk() {
      userStore.logout()
      router.push('/login/student')
    }
  })
}
</script>

<style scoped>
/* ========== Design System Variables ========== */
.app-layout {
  --color-primary: #0369A1;
  --color-secondary: #0EA5E9;
  --color-cta: #22C55E;
  --color-bg: #F0F9FF;
  --color-text: #0C4A6E;
  --color-text-muted: #64748B;
  --color-surface: #FFFFFF;
  --color-border: rgba(255, 255, 255, 0.2);

  --shadow-sm: 0 2px 8px rgba(3, 105, 161, 0.08);
  --shadow-md: 0 4px 16px rgba(3, 105, 161, 0.12);
  --shadow-lg: 0 8px 32px rgba(3, 105, 161, 0.16);

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  --transition-fast: 0.15s ease-out;
  --transition-normal: 0.25s ease-out;

  min-height: 100vh;
  font-family: 'Poppins', 'Open Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ========== Glassmorphism Header ========== */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  padding: 0 32px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  width: 100%;
  height: 64px;
  transition: background 0.3s ease, box-shadow 0.3s ease;
}

/* 学生端 - 紫蓝色 */
.app-header-student {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.9) 100%);
  box-shadow: 0 4px 24px rgba(102, 126, 234, 0.25);
}

/* 企业端 - 清爽蓝 (浅一点) */
.app-header-enterprise {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.95) 0%, rgba(99, 102, 241, 0.9) 100%);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.25);
}

/* 高校端 - 青蓝色 */
.app-header-university {
  background: linear-gradient(135deg, rgba(79, 172, 254, 0.95) 0%, rgba(0, 242, 254, 0.9) 100%);
  box-shadow: 0 4px 24px rgba(79, 172, 254, 0.25);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 26px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: white;
  white-space: nowrap;
  letter-spacing: -0.02em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: white;
  margin: 0 4px;
  font-weight: 500;
  font-size: 14px;
}

.header-btn {
  color: rgba(255, 255, 255, 0.9) !important;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
}

.header-btn:hover {
  color: white !important;
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.header-btn:active {
  transform: translateY(0);
  background: rgba(255, 255, 255, 0.25);
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.4) !important;
  border-color: rgba(239, 68, 68, 0.5) !important;
  color: #fef2f2 !important;
}

/* ========== Main Content ========== */
.app-content {
  padding: 24px;
  padding-top: 88px;
  background: #ffffff;
  min-height: calc(100vh - 64px);
}

.app-content.no-header {
  padding: 0;
  margin: 0;
  min-height: 100vh;
  background: transparent;
}

/* ========== Footer ========== */
.app-footer {
  text-align: center;
  background: #ffffff;
  color: var(--color-text-muted);
  padding: 24px;
  font-size: 13px;
  border-top: 1px solid rgba(3, 105, 161, 0.1);
}
</style>

<!-- Global Styles (Unscoped) -->
<style>
/* Google Fonts Import */
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap');

/* Global Font Family */
body {
  font-family: 'Poppins', 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ========== Overlay Scrollbar (Floating) ========== */
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(3, 105, 161, 0.3) transparent;
}

*::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

*::-webkit-scrollbar-track {
  background: transparent;
}

*::-webkit-scrollbar-thumb {
  background: rgba(3, 105, 161, 0.2);
  border-radius: 3px;
  transition: background 0.2s ease-out;
}

*::-webkit-scrollbar-thumb:hover {
  background: rgba(3, 105, 161, 0.4);
}

/* Show scrollbar only on hover */
*::-webkit-scrollbar-thumb {
  background: transparent;
}

*:hover::-webkit-scrollbar-thumb {
  background: rgba(3, 105, 161, 0.25);
}

*:hover::-webkit-scrollbar-thumb:hover {
  background: rgba(3, 105, 161, 0.45);
}

/* Overlay scrollbar for specific containers */
.ant-modal-body,
.ant-table-body,
.ant-select-dropdown,
.ant-dropdown {
  overflow: overlay !important;
}

/* ========== Global Button Enhancements ========== */
.ant-btn {
  font-family: 'Poppins', sans-serif;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.2s ease-out;
}

.ant-btn-primary {
  background: linear-gradient(135deg, #0369A1 0%, #0EA5E9 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(3, 105, 161, 0.25);
}

.ant-btn-primary:hover {
  background: linear-gradient(135deg, #0284C7 0%, #38BDF8 100%);
  box-shadow: 0 4px 16px rgba(3, 105, 161, 0.35);
  transform: translateY(-1px);
}

/* ========== Global Card Enhancements ========== */
.ant-card {
  border-radius: 12px;
  border: 1px solid rgba(3, 105, 161, 0.08);
  box-shadow: 0 2px 12px rgba(3, 105, 161, 0.06);
  transition: all 0.25s ease-out;
}

.ant-card:hover {
  box-shadow: 0 4px 20px rgba(3, 105, 161, 0.12);
}

/* ========== Global Modal Enhancements ========== */
.ant-modal-content {
  border-radius: 16px;
  overflow: hidden;
}

.ant-modal-header {
  background: linear-gradient(135deg, #0369A1 0%, #0EA5E9 100%);
  border-bottom: none;
  padding: 16px 24px;
}

.ant-modal-title {
  color: white !important;
  font-weight: 600;
}

.ant-modal-close {
  color: rgba(255, 255, 255, 0.8);
}

.ant-modal-close:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

/* ========== Global Input Enhancements ========== */
.ant-input,
.ant-select-selector,
.ant-picker {
  border-radius: 8px !important;
  transition: all 0.2s ease-out !important;
}

.ant-input:focus,
.ant-input-focused,
.ant-select-focused .ant-select-selector,
.ant-picker-focused {
  border-color: #0EA5E9 !important;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.15) !important;
}

/* ========== Global Table Enhancements ========== */
.ant-table {
  border-radius: 12px;
  overflow: hidden;
}

.ant-table-thead>tr>th {
  background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%) !important;
  font-weight: 600;
  color: #0C4A6E;
}

.ant-table-tbody>tr:hover>td {
  background: rgba(14, 165, 233, 0.04) !important;
}

/* ========== Global Tag Enhancements ========== */
.ant-tag {
  border-radius: 6px;
  font-weight: 500;
}

/* ========== Respect Reduced Motion ========== */
@media (prefers-reduced-motion: reduce) {

  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
