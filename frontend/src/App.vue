<template>
  <a-config-provider :locale="zhCN">
    <a-layout class="app-layout">
      <!-- 顶部导航（仅主页面显示，登录页不显示） -->
      <a-layout-header v-if="!isLoginPage" class="app-header">
        <div class="logo">
          <span class="logo-icon">🎓</span>
          <span class="logo-text">{{ currentTitle }}</span>
        </div>
        <div class="header-right" v-if="isLoggedIn">
          <a-tag color="rgba(255,255,255,0.2)" style="border: 1px solid rgba(255,255,255,0.3); color: white;">
            🆔 {{ userInfo?.student_id || userInfo?.user_id || '-' }}
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

      <!-- 页脚（登录页不显示） -->
      <a-layout-footer v-if="!isLoginPage" class="app-footer">
        智途AI就业推荐系统 ©2026 基于知识图谱与GraphSAGE
      </a-layout-footer>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Modal } from 'ant-design-vue'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { createVNode } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

const router = useRouter()
const route = useRoute()

// 判断是否是登录页
const isLoginPage = computed(() => route.path.startsWith('/login'))

// 判断是否已登录
const isLoggedIn = computed(() => !!localStorage.getItem('token'))

// 用户信息
const userInfo = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}')
  } catch {
    return {}
  }
})

// 当前页面标题
const currentTitle = computed(() => {
  if (route.path.startsWith('/student')) return '智途AI · 学生就业服务'
  if (route.path.startsWith('/enterprise')) return '智途AI · 企业人才招聘'
  if (route.path.startsWith('/university')) return '智途AI · 高校就业管理'
  return '智途AI就业推荐系统'
})

// 编辑资料 - 触发子组件的资料弹窗
const showProfileModal = () => {
  // 通过事件总线或直接调用子组件方法
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
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('studentId')
      localStorage.removeItem('role')
      router.push('/login/student')
    }
  })
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 0 24px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  width: 100%;
  height: 64px;
}

.logo {
  display: flex;
  align-items: center;
}

.logo-icon {
  font-size: 28px;
  margin-right: 12px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: white;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-name {
  color: white;
  margin: 0 8px;
  font-weight: 500;
}

.header-btn {
  color: rgba(255, 255, 255, 0.85) !important;
  font-size: 14px;
  padding: 4px 12px;
  border-radius: 6px;
  transition: all 0.3s ease;
  background: transparent;
}

.header-btn:hover {
  color: white !important;
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

.header-btn:active {
  transform: translateY(0);
  background: rgba(255, 255, 255, 0.25);
}

.logout-btn:hover {
  background: rgba(255, 100, 100, 0.3) !important;
  color: #ffcccc !important;
}

.app-content {
  padding: 24px;
  padding-top: 88px;
  /* 64px header + 24px spacing */
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.app-content.no-header {
  padding: 0;
  margin: 0;
  min-height: 100vh;
  background: transparent;
}

.app-footer {
  text-align: center;
  background: #f5f7fa;
  color: #999;
}
</style>
