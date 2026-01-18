import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/student'
  },
  {
    path: '/student',
    name: 'student',
    component: () => import('@/views/student/Dashboard.vue'),
    meta: { title: '学生端', theme: 'blue' }
  },
  {
    path: '/student/job/:id',
    name: 'jobDetail',
    component: () => import('@/views/student/JobDetail.vue'),
    meta: { title: '职位详情', theme: 'blue' }
  },
  {
    path: '/enterprise',
    name: 'enterprise',
    component: () => import('@/views/enterprise/TalentScout.vue'),
    meta: { title: '企业端', theme: 'purple' }
  },
  {
    path: '/enterprise/candidate/:id',
    name: 'candidateDetail',
    component: () => import('@/views/enterprise/CandidateDetail.vue'),
    meta: { title: '候选人详情', theme: 'purple' }
  },
  {
    path: '/university',
    name: 'university',
    component: () => import('@/views/university/GapAnalysis.vue'),
    meta: { title: '高校端', theme: 'orange' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
