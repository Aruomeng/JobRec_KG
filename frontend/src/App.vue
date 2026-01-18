<template>
  <a-config-provider :locale="zhCN">
    <a-layout class="app-layout">
      <!-- 顶部导航 -->
      <a-layout-header class="app-header">
        <div class="logo">
          <span class="logo-icon">🎓</span>
          <span class="logo-text">高校就业推荐系统</span>
        </div>
        <a-menu 
          v-model:selectedKeys="selectedKeys" 
          mode="horizontal" 
          :style="{ lineHeight: '64px', flex: 1 }"
          @click="handleMenuClick"
        >
          <a-menu-item key="student">
            <template #icon><UserOutlined /></template>
            学生端
          </a-menu-item>
          <a-menu-item key="enterprise">
            <template #icon><BankOutlined /></template>
            企业端
          </a-menu-item>
          <a-menu-item key="university">
            <template #icon><BookOutlined /></template>
            高校端
          </a-menu-item>
        </a-menu>
      </a-layout-header>
      
      <!-- 主体内容 -->
      <a-layout-content class="app-content">
        <router-view v-slot="{ Component }">
          <keep-alive :include="['StudentDashboard', 'TalentScout', 'GapAnalysis']">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </a-layout-content>
      
      <!-- 页脚 -->
      <a-layout-footer class="app-footer">
        高校就业推荐系统 ©2026 基于知识图谱与GraphSAGE
      </a-layout-footer>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { UserOutlined, BankOutlined, BookOutlined } from '@ant-design/icons-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

const router = useRouter()
const selectedKeys = ref(['student'])

const handleMenuClick = ({ key }) => {
  router.push(`/${key}`)
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #1890ff 0%, #722ed1 100%);
  padding: 0 24px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  width: 100%;
}

.logo {
  display: flex;
  align-items: center;
  margin-right: 24px;
}

.logo-icon {
  font-size: 28px;
  margin-right: 8px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: white;
  white-space: nowrap;
}

.app-header :deep(.ant-menu) {
  background: transparent;
  border-bottom: none;
}

.app-header :deep(.ant-menu-item) {
  color: rgba(255, 255, 255, 0.85);
}

.app-header :deep(.ant-menu-item-selected) {
  color: white;
  background: rgba(255, 255, 255, 0.2) !important;
  border-radius: 8px;
}

.app-content {
  padding: 24px;
  padding-top: 88px; /* 64px header + 24px spacing */
  background: #f0f2f5;
  min-height: calc(100vh - 64px);
}

.app-footer {
  text-align: center;
  background: #f0f2f5;
  color: #999;
}
</style>
