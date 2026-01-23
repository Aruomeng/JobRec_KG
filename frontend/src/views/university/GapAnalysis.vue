<template>
  <div class="university-portal">
    <!-- 页面标题 -->
    <a-page-header
      title="📊 高校智能分析平台"
      sub-title="课程供给 vs 市场需求全景透视"
      :style="{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        marginBottom: '24px',
        borderRadius: '12px',
        color: 'white',
      }"
    >
      <template #extra>
        <a-button type="primary" ghost @click="fetchData" :loading="loading">
          🔄 刷新数据
        </a-button>
      </template>
    </a-page-header>

    <!-- 顶部统计卡片 + 环形图 -->
    <a-row :gutter="16" class="stat-row">
      <a-col :span="6">
        <div
          class="stat-card-modern"
          style="background: linear-gradient(135deg, #fa8c16 0%, #f5222d 100%)"
        >
          <div class="stat-icon">🔥</div>
          <div class="stat-content">
            <div class="stat-value">{{ gaps.length }}</div>
            <div class="stat-label">技能缺口</div>
          </div>
        </div>
      </a-col>
      <a-col :span="6">
        <div
          class="stat-card-modern"
          style="background: linear-gradient(135deg, #1890ff 0%, #722ed1 100%)"
        >
          <div class="stat-icon">📚</div>
          <div class="stat-content">
            <div class="stat-value">{{ courses.length }}</div>
            <div class="stat-label">课程总数</div>
          </div>
        </div>
      </a-col>
      <a-col :span="6">
        <div
          class="stat-card-modern"
          style="background: linear-gradient(135deg, #52c41a 0%, #13c2c2 100%)"
        >
          <div class="stat-icon">✅</div>
          <div class="stat-content">
            <div class="stat-value">{{ highRelevanceCourses }}</div>
            <div class="stat-label">高关联课程</div>
          </div>
        </div>
      </a-col>
      <a-col :span="6">
        <div
          class="stat-card-modern"
          style="background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%)"
        >
          <div class="stat-icon">⚠️</div>
          <div class="stat-content">
            <div class="stat-value">{{ lowRelevanceCourses }}</div>
            <div class="stat-label">低效课程</div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- Tab切换 -->
    <a-tabs v-model:activeKey="activeTab" size="large" type="card">
      <!-- Gap分析 -->
      <a-tab-pane key="gap" tab="🔥 技能缺口分析">
        <a-spin :spinning="loading">
          <a-row :gutter="16">
            <!-- 左侧：技能缺口条形图 -->
            <a-col :span="14">
              <a-card
                title="📊 技能市场需求 TOP 15"
                :bordered="false"
                class="chart-card"
              >
                <div style="height: 400px">
                  <v-chart
                    :option="gapBarOption"
                    autoresize
                    style="width: 100%; height: 100%"
                  />
                </div>
              </a-card>
            </a-col>

            <!-- 右侧：缺口分布饼图 + 急需技能列表 -->
            <a-col :span="10">
              <a-card
                title="🎯 课程供给分布"
                :bordered="false"
                class="chart-card"
                style="margin-bottom: 16px"
              >
                <div style="height: 180px">
                  <v-chart
                    :option="supplyPieOption"
                    autoresize
                    style="width: 100%; height: 100%"
                  />
                </div>
              </a-card>

              <a-card
                title="🚨 急需开设课程的技能"
                :bordered="false"
                class="chart-card"
              >
                <div class="urgent-skill-list">
                  <div
                    v-for="(gap, index) in urgentGaps"
                    :key="gap.skill"
                    class="urgent-skill-item"
                    :style="{ animationDelay: `${index * 0.1}s` }"
                  >
                    <div class="skill-rank">{{ index + 1 }}</div>
                    <div class="skill-info">
                      <div class="skill-name">{{ gap.skill }}</div>
                      <div class="skill-demand">
                        需求 {{ gap.market_demand }} 个职位
                      </div>
                    </div>
                    <a-tag :color="gap.supply_courses === 0 ? 'red' : 'orange'">
                      {{
                        gap.supply_courses === 0
                          ? "无课程"
                          : `${gap.supply_courses}门课程`
                      }}
                    </a-tag>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </a-spin>
      </a-tab-pane>

      <!-- 课程健康度 -->
      <a-tab-pane key="health" tab="📈 课程健康度">
        <a-spin :spinning="loading">
          <a-row :gutter="16">
            <!-- 左侧：课程健康度雷达图 -->
            <a-col :span="10">
              <a-card
                title="🎯 课程综合评估"
                :bordered="false"
                class="chart-card"
              >
                <div style="height: 320px">
                  <v-chart
                    :option="courseRadarOption"
                    autoresize
                    style="width: 100%; height: 100%"
                  />
                </div>
              </a-card>
            </a-col>

            <!-- 右侧：课程趋势分布 -->
            <a-col :span="14">
              <a-card
                title="📊 课程选课热度 TOP 10"
                :bordered="false"
                class="chart-card"
              >
                <div style="height: 320px">
                  <v-chart
                    :option="enrollmentBarOption"
                    autoresize
                    style="width: 100%; height: 100%"
                  />
                </div>
              </a-card>
            </a-col>
          </a-row>

          <!-- 课程列表卡片 -->
          <a-row :gutter="16" style="margin-top: 16px">
            <a-col :span="24">
              <a-card title="📚 课程详情" :bordered="false" class="chart-card">
                <div class="course-grid">
                  <div
                    v-for="course in courses.slice(0, 12)"
                    :key="course.name"
                    class="course-item"
                    :class="getCourseClass(course)"
                  >
                    <div class="course-header">
                      <span class="course-name">{{ course.name }}</span>
                      <a-tag
                        :color="getTrendTagColor(course.trend)"
                        size="small"
                        >{{ course.trend }}</a-tag
                      >
                    </div>
                    <div class="course-stats">
                      <div class="course-stat">
                        <span class="stat-num">{{ course.enrollment }}</span>
                        <span class="stat-desc">选课人数</span>
                      </div>
                      <div class="course-stat">
                        <span class="stat-num">{{ course.skill_count }}</span>
                        <span class="stat-desc">技能数</span>
                      </div>
                      <div class="course-stat">
                        <span
                          class="stat-num"
                          :style="{
                            color: getRelevanceColor(course.job_relevance),
                          }"
                        >
                          {{ Math.round(course.job_relevance * 100) }}%
                        </span>
                        <span class="stat-desc">关联度</span>
                      </div>
                    </div>
                    <a-progress
                      :percent="Math.round(course.job_relevance * 100)"
                      :stroke-color="getRelevanceColor(course.job_relevance)"
                      :show-info="false"
                      size="small"
                    />
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </a-spin>
      </a-tab-pane>

      <!-- 改革建议 -->
      <a-tab-pane key="reform" tab="💡 改革建议">
        <a-spin :spinning="loading">
          <div v-if="reformSuggestions">
            <!-- 总结卡片 -->
            <a-card class="summary-card" :bordered="false">
              <div class="summary-content">
                <div class="summary-icon">💡</div>
                <div class="summary-text">{{ reformSuggestions.summary }}</div>
              </div>
            </a-card>

            <a-row :gutter="16" style="margin-top: 16px">
              <!-- 急需技能柱状图 -->
              <a-col :span="12">
                <a-card
                  title="🔥 急需技能市场需求"
                  :bordered="false"
                  class="chart-card"
                >
                  <div style="height: 300px">
                    <v-chart
                      :option="urgentSkillBarOption"
                      autoresize
                      style="width: 100%; height: 100%"
                    />
                  </div>
                </a-card>
              </a-col>

              <!-- 低效课程列表 -->
              <a-col :span="12">
                <a-card
                  title="⚠️ 需要评估的课程"
                  :bordered="false"
                  class="chart-card"
                >
                  <div class="low-eff-list">
                    <div
                      v-for="(
                        item, index
                      ) in reformSuggestions.low_relevance_courses"
                      :key="item.course"
                      class="low-eff-item"
                    >
                      <div class="low-eff-rank" :class="'rank-' + (index + 1)">
                        {{ index + 1 }}
                      </div>
                      <div class="low-eff-info">
                        <div class="low-eff-name">{{ item.course }}</div>
                        <a-progress
                          :percent="Math.round(item.relevance * 100)"
                          :stroke-color="
                            item.relevance > 0.3 ? '#faad14' : '#ff4d4f'
                          "
                          size="small"
                          :format="() => `${Math.round(item.relevance * 100)}%`"
                        />
                      </div>
                      <a-tag color="volcano">需评估</a-tag>
                    </div>
                    <a-empty
                      v-if="!reformSuggestions.low_relevance_courses?.length"
                      description="暂无低效课程"
                    />
                  </div>
                </a-card>
              </a-col>
            </a-row>
          </div>
        </a-spin>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { message } from "ant-design-vue";
import { universityApi } from "@/api";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, PieChart, RadarChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
} from "echarts/components";

// 注册 ECharts 组件
use([
  CanvasRenderer,
  BarChart,
  PieChart,
  RadarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
]);

const activeTab = ref("gap");
const loading = ref(false);
const gaps = ref([]);
const courses = ref([]);
const reformSuggestions = ref(null);

// 计算属性
const highRelevanceCourses = computed(
  () => courses.value.filter((c) => c.job_relevance >= 0.5).length,
);

const lowRelevanceCourses = computed(
  () => courses.value.filter((c) => c.job_relevance < 0.2).length,
);

const urgentGaps = computed(() =>
  gaps.value.filter((g) => g.supply_courses <= 1).slice(0, 6),
);

// 技能缺口条形图配置
const gapBarOption = computed(() => {
  const topGaps = gaps.value.slice(0, 15);
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: {
      left: "3%",
      right: "8%",
      top: "8%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: { type: "value", name: "职位需求数" },
    yAxis: {
      type: "category",
      data: topGaps.map((g) => g.skill).reverse(),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: topGaps
          .map((g) => ({
            value: g.market_demand,
            itemStyle: {
              color:
                g.supply_courses === 0
                  ? {
                      type: "linear",
                      x: 0,
                      y: 0,
                      x2: 1,
                      y2: 0,
                      colorStops: [
                        { offset: 0, color: "#ff4d4f" },
                        { offset: 1, color: "#f5222d" },
                      ],
                    }
                  : g.supply_courses <= 2
                    ? {
                        type: "linear",
                        x: 0,
                        y: 0,
                        x2: 1,
                        y2: 0,
                        colorStops: [
                          { offset: 0, color: "#faad14" },
                          { offset: 1, color: "#fa8c16" },
                        ],
                      }
                    : {
                        type: "linear",
                        x: 0,
                        y: 0,
                        x2: 1,
                        y2: 0,
                        colorStops: [
                          { offset: 0, color: "#52c41a" },
                          { offset: 1, color: "#389e0d" },
                        ],
                      },
              borderRadius: [0, 4, 4, 0],
            },
          }))
          .reverse(),
        barWidth: 16,
        label: { show: true, position: "right", fontSize: 10 },
      },
    ],
  };
});

// 课程供给饼图
const supplyPieOption = computed(() => {
  const noSupply = gaps.value.filter((g) => g.supply_courses === 0).length;
  const lowSupply = gaps.value.filter(
    (g) => g.supply_courses === 1 || g.supply_courses === 2,
  ).length;
  const goodSupply = gaps.value.filter((g) => g.supply_courses >= 3).length;

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { orient: "vertical", right: 10, top: "center" },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["35%", "50%"],
        avoidLabelOverlap: false,
        label: { show: false },
        data: [
          { value: noSupply, name: "无课程", itemStyle: { color: "#ff4d4f" } },
          {
            value: lowSupply,
            name: "供给不足",
            itemStyle: { color: "#faad14" },
          },
          {
            value: goodSupply,
            name: "供给充足",
            itemStyle: { color: "#52c41a" },
          },
        ],
      },
    ],
  };
});

// 课程选课热度条形图
const enrollmentBarOption = computed(() => {
  const topCourses = [...courses.value]
    .sort((a, b) => b.enrollment - a.enrollment)
    .slice(0, 10);
  return {
    tooltip: { trigger: "axis" },
    grid: {
      left: "3%",
      right: "10%",
      top: "5%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: { type: "value", name: "选课人数" },
    yAxis: {
      type: "category",
      data: topCourses
        .map((c) => (c.name.length > 10 ? c.name.slice(0, 10) + "..." : c.name))
        .reverse(),
      axisLabel: { fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        data: topCourses
          .map((c) => ({
            value: c.enrollment,
            itemStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 1,
                y2: 0,
                colorStops: [
                  { offset: 0, color: "#667eea" },
                  { offset: 1, color: "#764ba2" },
                ],
              },
              borderRadius: [0, 4, 4, 0],
            },
          }))
          .reverse(),
        barWidth: 14,
        label: { show: true, position: "right", fontSize: 10 },
      },
    ],
  };
});

// 课程综合评估雷达图
const courseRadarOption = computed(() => {
  const avgEnrollment = courses.value.length
    ? courses.value.reduce((a, c) => a + c.enrollment, 0) / courses.value.length
    : 0;
  const avgSkillCount = courses.value.length
    ? courses.value.reduce((a, c) => a + c.skill_count, 0) /
      courses.value.length
    : 0;
  const avgRelevance = courses.value.length
    ? courses.value.reduce((a, c) => a + c.job_relevance, 0) /
      courses.value.length
    : 0;
  const upTrend = courses.value.filter((c) => c.trend.includes("上升")).length;
  const stableTrend = courses.value.filter((c) =>
    c.trend.includes("稳定"),
  ).length;

  return {
    tooltip: {},
    radar: {
      indicator: [
        { name: "平均选课人数", max: 50 },
        { name: "平均技能数", max: 5 },
        { name: "平均关联度", max: 1 },
        { name: "上升趋势", max: 30 },
        { name: "稳定课程", max: 30 },
      ],
      radius: "65%",
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: [
              avgEnrollment,
              avgSkillCount,
              avgRelevance,
              upTrend,
              stableTrend,
            ],
            name: "课程体系",
            areaStyle: { color: "rgba(102, 126, 234, 0.4)" },
            lineStyle: { color: "#667eea" },
          },
        ],
      },
    ],
  };
});

// 急需技能柱状图
const urgentSkillBarOption = computed(() => {
  const skills = reformSuggestions.value?.urgent_skills || [];
  return {
    tooltip: { trigger: "axis" },
    grid: {
      left: "3%",
      right: "10%",
      top: "5%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: { type: "value", name: "市场需求" },
    yAxis: {
      type: "category",
      data: skills.map((s) => s.skill).reverse(),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: skills
          .map((s) => ({
            value: s.demand,
            itemStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 1,
                y2: 0,
                colorStops: [
                  { offset: 0, color: "#ff4d4f" },
                  { offset: 1, color: "#f5222d" },
                ],
              },
              borderRadius: [0, 4, 4, 0],
            },
          }))
          .reverse(),
        barWidth: 18,
        label: { show: true, position: "right", fontSize: 10 },
      },
    ],
  };
});

// 工具函数
const getRelevanceColor = (relevance) => {
  if (relevance >= 0.5) return "#52c41a";
  if (relevance >= 0.2) return "#faad14";
  return "#ff4d4f";
};

const getTrendTagColor = (trend) => {
  if (trend.includes("上升")) return "success";
  if (trend.includes("下降")) return "error";
  return "processing";
};

const getCourseClass = (course) => {
  if (course.job_relevance >= 0.5) return "course-high";
  if (course.job_relevance < 0.2) return "course-low";
  return "course-medium";
};

const fetchData = async () => {
  loading.value = true;
  try {
    const [gapRes, courseRes, reformRes] = await Promise.all([
      universityApi.analyzeSkillGap(20),
      universityApi.evaluateCourses(30),
      universityApi.getReformSuggestions(),
    ]);

    gaps.value = gapRes.data.gaps;
    courses.value = courseRes.data.courses;
    reformSuggestions.value = reformRes.data;

    message.success("数据加载完成");
  } catch (error) {
    message.error("数据加载失败");
    console.error(error);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchData);
</script>

<style scoped>
.university-portal {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 16px;
}

/* 统计卡片 */
.stat-row {
  margin-bottom: 24px;
}

.stat-card-modern {
  border-radius: 16px;
  padding: 20px;
  color: white;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition:
    transform 0.3s,
    box-shadow 0.3s;
}

.stat-card-modern:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.stat-icon {
  font-size: 36px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 4px;
}

/* 图表卡片 */
.chart-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 急需技能列表 */
.urgent-skill-list {
  max-height: 200px;
  overflow-y: auto;
}

.urgent-skill-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fafafa;
  margin-bottom: 8px;
  animation: fadeInUp 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.skill-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff4d4f, #f5222d);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  margin-right: 12px;
}

.skill-info {
  flex: 1;
}

.skill-name {
  font-weight: 500;
  font-size: 14px;
}

.skill-demand {
  font-size: 12px;
  color: #666;
}

/* 课程网格 */
.course-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.course-item {
  padding: 14px;
  border-radius: 10px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  transition: all 0.3s;
}

.course-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.course-high {
  border-left: 3px solid #52c41a;
}

.course-medium {
  border-left: 3px solid #faad14;
}

.course-low {
  border-left: 3px solid #ff4d4f;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.course-name {
  font-weight: 500;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.course-stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.course-stat {
  text-align: center;
}

.stat-num {
  font-size: 16px;
  font-weight: 600;
}

.stat-desc {
  font-size: 10px;
  color: #999;
}

/* 总结卡片 */
.summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.summary-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.summary-icon {
  font-size: 48px;
}

.summary-text {
  font-size: 16px;
  line-height: 1.6;
}

/* 低效课程列表 */
.low-eff-list {
  max-height: 280px;
  overflow-y: auto;
}

.low-eff-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: #fff7e6;
  border-radius: 8px;
  margin-bottom: 8px;
}

.low-eff-rank {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: #faad14;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  margin-right: 12px;
}

.rank-1 {
  background: #ff4d4f;
}
.rank-2 {
  background: #fa8c16;
}
.rank-3 {
  background: #faad14;
}

.low-eff-info {
  flex: 1;
}

.low-eff-name {
  font-weight: 500;
  margin-bottom: 4px;
}

:deep(.ant-tabs-card > .ant-tabs-nav .ant-tabs-tab) {
  border-radius: 8px 8px 0 0;
  background: #fafafa;
}

:deep(.ant-tabs-card > .ant-tabs-nav .ant-tabs-tab-active) {
  background: white;
}

:deep(.ant-page-header-heading-title),
:deep(.ant-page-header-heading-sub-title) {
  color: white !important;
}
</style>
