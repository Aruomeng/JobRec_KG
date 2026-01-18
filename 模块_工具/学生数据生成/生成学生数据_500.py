#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成500名学生数据用于GraphSAGE训练
====================================
包含学历、期望城市等属性
"""

import json
import random
from datetime import datetime

# 从data_main读取专业数据
domain_data = {
    "物联网工程": {"物联网导论": ["IoT概念","传感器技术","RFID"], "嵌入式系统设计": ["C语言","ARM架构","Linux驱动"], "无线传感器网络": ["ZigBee","蓝牙","Wi-Fi协议"], "RFID原理及应用": ["RFID","射频识别","NFC"], "单片机原理": ["STM32","C语言","汇编语言"], "传感器技术": ["传感器","模数转换","信号处理"], "物联网通信技术": ["NB-IoT","LoRa","5G技术"], "Python物联网开发": ["Python","MQTT协议","Socket编程"], "物联网信息安全": ["网络安全","加密算法","数据隐私"], "云计算与物联网": ["云计算","AWS","边缘计算"]},
    "计算机科学与技术": {"C++程序设计": ["C++","面向对象","STL库"], "Java语言程序设计": ["Java","JVM","多线程"], "数据结构与算法": ["算法","数据结构","逻辑思维"], "计算机网络": ["TCP/IP","HTTP协议","网络编程"], "操作系统原理": ["Linux","Shell脚本","进程管理"], "数据库系统概论": ["MySQL","SQL","数据库设计"], "计算机组成原理": ["计算机体系结构","汇编语言","硬件基础"], "编译原理": ["编译技术","词法分析","正则表达式"], "Web前端开发": ["HTML/CSS","JavaScript","Vue.js"], "软件工程导论": ["敏捷开发","UML建模","Git"]},
    "软件工程": {"Java企业级开发": ["Java","Spring Boot","MyBatis"], "Web应用开发": ["React","JavaScript","Node.js"], "软件测试技术": ["软件测试","Selenium","JUnit"], "移动应用开发": ["Android","Kotlin","Flutter"], "软件项目管理": ["项目管理","JIRA","Scrum"], "设计模式": ["设计模式","重构","面向对象"], "数据库应用": ["MySQL","Redis","MongoDB"], "Linux操作系统": ["Linux","Shell","运维基础"], "DevOps实践": ["Docker","Kubernetes","Jenkins"], "中间件技术": ["消息队列","Kafka","Nginx"]},
    "大数据管理与应用": {"Python数据分析": ["Python","Pandas","NumPy"], "Hadoop大数据技术": ["Hadoop","MapReduce","HDFS"], "Spark大数据处理": ["Spark","Scala","分布式计算"], "数据可视化": ["ECharts","Tableau","Matplotlib"], "NoSQL数据库": ["Redis","MongoDB","HBase"], "机器学习导论": ["Scikit-learn","机器学习","统计学"], "数据挖掘": ["数据挖掘","关联规则","聚类算法"], "网络爬虫技术": ["Python","Scrapy","网络爬虫"], "商业智能BI": ["PowerBI","数据仓库","ETL"], "统计学基础": ["SPSS","概率论","A/B测试"]},
    "电子信息工程": {"电路分析基础": ["电路设计","Multisim","电子元器件"], "模拟电子技术": ["模电","晶体管","放大电路"], "数字电子技术": ["数电","FPGA","Verilog"], "信号与系统": ["信号处理","MATLAB","傅里叶变换"], "数字信号处理": ["DSP","滤波器设计","MATLAB"], "EDA技术": ["PCB设计","Altium Designer","Protell"], "嵌入式开发": ["C语言","Keil","微控制器"], "微机原理": ["汇编语言","接口技术","计算机硬件"], "电磁场与电磁波": ["电磁兼容","天线设计","微波技术"], "通信电路": ["通信原理","高频电路","锁相环"]},
    "通信工程": {"通信原理": ["通信系统","调制解调","信道编码"], "移动通信": ["4G/5G","LTE","无线网络"], "光纤通信": ["光网络","光传输","OTN"], "计算机网络与协议": ["TCP/IP","路由交换","Cisco配置"], "交换技术": ["SDN","网络架构","软交换"], "天线与电波传播": ["天线设计","HFSS","电磁波"], "信号处理实验": ["MATLAB","Simulink","数据分析"], "C语言程序设计": ["C语言","嵌入式编程","算法"], "下一代网络技术": ["IPv6","IoT","网络切片"], "网络规划与优化": ["网络优化","基站维护","路测"]},
    "人工智能": {"人工智能导论": ["AI概念","专家系统","知识图谱"], "深度学习": ["TensorFlow","PyTorch","神经网络"], "计算机视觉": ["OpenCV","图像处理","CNN"], "自然语言处理": ["NLP","BERT","文本分析"], "强化学习": ["强化学习","Q-Learning","智能体"], "模式识别": ["模式识别","SVM","贝叶斯分类"], "Python高阶编程": ["Python","并发编程","装饰器"], "高等数学": ["微积分","线性代数","数学建模"], "Linux环境编程": ["Linux","Shell","C++"], "机器人技术": ["ROS","SLAM","路径规划"]},
    "网络工程": {"路由与交换技术": ["Cisco","华为认证","VLAN"], "网络安全技术": ["防火墙","VPN","入侵检测"], "Windows Server管理": ["Windows Server","AD域","系统管理"], "Linux网络管理": ["CentOS","Shell","Apache/Nginx"], "网络规划设计": ["Visio","网络拓扑","综合布线"], "网络存储技术": ["SAN","NAS","RAID"], "云计算架构": ["OpenStack","KVM","虚拟化"], "Python运维开发": ["Python","Ansible","自动化运维"], "Web安全攻防": ["SQL注入","XSS","渗透测试"], "SDN技术": ["SDN","OpenFlow","Mininet"]},
    "信息安全": {"密码学": ["加密算法","RSA","区块链基础"], "操作系统安全": ["Linux安全","权限管理","安全加固"], "网络攻防实践": ["CTF","Metasploit","Kali Linux"], "恶意代码分析": ["逆向工程","IDA Pro","汇编语言"], "Web应用安全": ["BurpSuite","OWASP Top10","漏洞扫描"], "信息隐藏技术": ["数字水印","隐写术","信息隐藏"], "数据库安全": ["SQL审计","数据脱敏","数据库防火墙"], "风险评估与管理": ["等级保护","ISO27001","风险评估"], "计算机取证": ["电子取证","数据恢复","日志分析"], "Python黑客编程": ["Python","Socket","Scapy"]},
    "电子商务": {"电子商务概论": ["电商模式","B2B/B2C","O2O"], "网络营销": ["SEO/SEM","新媒体运营","用户增长"], "网页设计与制作": ["HTML/CSS","Dreamweaver","UI设计"], "商务数据分析": ["Excel","Python","数据报表"], "供应链管理": ["ERP系统","物流管理","库存控制"], "客户关系管理": ["CRM","Salesforce","用户画像"], "移动电商开发": ["小程序开发","微信生态","JavaScript"], "电子支付与结算": ["第三方支付","金融科技","区块链"], "电商系统设计": ["UML","需求分析","Axure原型"], "推荐系统导论": ["推荐算法","协同过滤","用户行为分析"]}
}

# 姓名库
SURNAMES = ['王','李','张','刘','陈','杨','赵','黄','周','吴','徐','孙','胡','朱','高','林','何','郭','马','罗','梁','宋','郑','谢','韩','唐','冯','于','董','萧','程','曹','袁','邓','许','傅','沈','曾','彭','吕','苏','卢','蒋','蔡','贾','丁','魏','薛','叶','阎']
NAMES = ['伟','芳','娜','秀英','敏','静','丽','强','磊','军','洋','勇','艳','杰','涛','明','超','秀兰','霞','平','刚','桂英','娟','鑫','浩','宇','宁','帆','晨','阳','思','佳','雨','欣','雪','婷','凯','鹏','辉','威','龙','文','博','翔','晓','志','嘉','子','梓','泽','俊','昊','睿','宸','航','轩','皓','奕','逸','熙']

# 城市列表  
CITIES = ['北京','上海','深圳','杭州','南京','成都','武汉','郑州','厦门']

# 城市分层（用于期望城市倾向）
TIER1_CITIES = ['北京','上海','深圳']  # 一线
TIER15_CITIES = ['杭州','南京','成都']  # 新一线
TIER2_CITIES = ['武汉','郑州','厦门']   # 二线

# 学历权重（中位数为本科）
EDUCATION_WEIGHTS = {
    '大专': 15,
    '本科': 60,
    '硕士': 20,
    '博士': 5
}

def generate_name():
    """生成随机姓名"""
    surname = random.choice(SURNAMES)
    if random.random() < 0.6:
        name = random.choice(NAMES)
    else:
        name = random.choice(NAMES) + random.choice(NAMES)
    return surname + name

def generate_education():
    """生成学历"""
    educations = list(EDUCATION_WEIGHTS.keys())
    weights = list(EDUCATION_WEIGHTS.values())
    return random.choices(educations, weights=weights)[0]

def generate_preferred_cities():
    """生成期望城市（1-3个）"""
    num_cities = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
    
    # 根据权重选择城市类型
    city_type = random.choices(
        ['tier1', 'tier15', 'tier2'],
        weights=[0.40, 0.35, 0.25]
    )[0]
    
    if city_type == 'tier1':
        pool = TIER1_CITIES
    elif city_type == 'tier15':
        pool = TIER15_CITIES
    else:
        pool = TIER2_CITIES
    
    # 可能跨类别选择
    if num_cities > len(pool):
        pool = CITIES
    
    return random.sample(pool, min(num_cities, len(pool)))

def generate_students(count=500):
    """生成指定数量的学生"""
    students = []
    majors = list(domain_data.keys())
    
    for i in range(1, count + 1):
        student_id = f"STU{i:04d}"
        name = generate_name()
        education = generate_education()
        major = random.choice(majors)
        preferred_cities = generate_preferred_cities()
        
        # 选择课程（4-8门）
        all_courses = list(domain_data[major].keys())
        num_courses = random.randint(4, min(8, len(all_courses)))
        selected_course_names = random.sample(all_courses, num_courses)
        
        # 构建课程和技能
        courses = []
        all_skills = set()
        
        for course_name in selected_course_names:
            skills = domain_data[major][course_name]
            courses.append({
                'name': course_name,
                'skills': skills
            })
            all_skills.update(skills)
        
        student = {
            'student_id': student_id,
            'name': name,
            'education': education,
            'major': major,
            'preferred_cities': preferred_cities,  # 新增
            'courses': courses,
            'skills': sorted(list(all_skills))
        }
        students.append(student)
    
    return students

def main():
    print("="*60)
    print("🎓 生成GraphSAGE训练用学生数据")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 生成500名学生
    students = generate_students(500)
    
    # 统计
    ed_count = {}
    major_count = {}
    city_count = {}
    
    for s in students:
        ed_count[s['education']] = ed_count.get(s['education'], 0) + 1
        major_count[s['major']] = major_count.get(s['major'], 0) + 1
        for city in s['preferred_cities']:
            city_count[city] = city_count.get(city, 0) + 1
    
    print(f"\n✅ 已生成 {len(students)} 名学生\n")
    
    print("📊 学历分布:")
    for edu, count in sorted(ed_count.items(), key=lambda x: -x[1]):
        print(f"   • {edu}: {count} 人 ({count/len(students)*100:.1f}%)")
    
    print("\n📚 专业分布 (Top 5):")
    for major, count in sorted(major_count.items(), key=lambda x: -x[1])[:5]:
        print(f"   • {major}: {count} 人")
    
    print("\n🌆 期望城市分布:")
    for city, count in sorted(city_count.items(), key=lambda x: -x[1]):
        print(f"   • {city}: {count} 次")
    
    # 样例
    print("\n👤 学生样例 (前3名):")
    print("-"*80)
    for s in students[:3]:
        print(f"\n{s['student_id']} - {s['name']}")
        print(f"  学历: {s['education']} | 专业: {s['major']}")
        print(f"  期望城市: {', '.join(s['preferred_cities'])}")
        print(f"  课程数: {len(s['courses'])} | 技能数: {len(s['skills'])}")
        print(f"  技能样例: {', '.join(s['skills'][:5])}...")
    print("-"*80)
    
    # 保存
    output = {
        'students': students,
        'domain_data': domain_data,
        'stats': {
            'total': len(students),
            'education_dist': ed_count,
            'major_dist': major_count,
            'city_dist': city_count
        },
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    output_file = 'students_data_500.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 数据已保存到: {output_file}")
    print("="*60)

if __name__ == '__main__':
    main()
