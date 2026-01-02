#!/usr/bin/env python
"""One-time script to load mock data."""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from api.models import (
    Agent, Conversation, Message, Requirement, DeliveryStandard,
    Project, Task, TeamMember, AgentThinking, AgentTaskItem,
    AgentCollaboration, Folder, File
)

# Clear existing data
print("Clearing existing data...")
File.objects.all().delete()
Folder.objects.all().delete()
AgentCollaboration.objects.all().delete()
AgentTaskItem.objects.all().delete()
AgentThinking.objects.all().delete()
Task.objects.all().delete()
TeamMember.objects.all().delete()
DeliveryStandard.objects.all().delete()
Requirement.objects.all().delete()
Message.objects.all().delete()
Conversation.objects.all().delete()
Project.objects.all().delete()
Agent.objects.all().delete()

# Reset auto-increment sequences (database-specific)
from django.db import connection
from django.conf import settings

db_engine = settings.DATABASES['default']['ENGINE']
if 'sqlite' in db_engine:
    # SQLite: Reset sqlite_sequence table
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('api_agent', 'api_project', 'api_conversation', 'api_message', 'api_requirement', 'api_deliverystandard', 'api_teammember', 'api_task', 'api_agentthinking', 'api_agenttaskitem', 'api_agentcollaboration', 'api_folder', 'api_file');")
        cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('api_project', 2);")
        cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('api_conversation', 4);")
    print("Reset SQLite auto-increment sequences.")
elif 'postgresql' in db_engine:
    # PostgreSQL: Reset sequences using ALTER SEQUENCE
    with connection.cursor() as cursor:
        tables = ['api_agent', 'api_project', 'api_conversation', 'api_message',
                  'api_requirement', 'api_deliverystandard', 'api_teammember',
                  'api_task', 'api_agentthinking', 'api_agenttaskitem',
                  'api_agentcollaboration', 'api_folder', 'api_file']
        for table in tables:
            try:
                cursor.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1;")
            except Exception:
                pass  # Sequence might not exist
        # Set specific starting values
        # Conversations start at 1 (for homepage: 4 conversations with IDs 1-4)
        # Project starts at 3 (legacy requirement)
        cursor.execute("ALTER SEQUENCE api_project_id_seq RESTART WITH 3;")
        cursor.execute("ALTER SEQUENCE api_conversation_id_seq RESTART WITH 1;")
    print("Reset PostgreSQL sequences.")
else:
    print("Unknown database engine, skipping sequence reset.")

# Create Agents from Excel data
print("Creating agents...")
agents_data = [
    {
        "agent_no": "Agent No.1",
        "name": "项目总策划",
        "duty": "项目总策划",
        "detail": """能产出的内容:

一、方案类文件
《崇明岛露营团建 · 整体策划方案》（Word/PDF）
《崇明岛团建 · 对领导汇报版 PPT》
《项目时间线 · 甘特图（Excel）》
《团建执行流程图（Flow Chart）》
《项目 RACI 表（责任矩阵）》
《团建当天逐分钟执行脚本（Timeline Script）》

二、管理类文件
《项目任务总表（Notion/Trello 模板）》
《人力分工表（Who does what）》
《预算总表（Excel）》
《风险预案（天气/安全/延误）》
《团建通知 · 给同事的行前须知（通知图 or 文案）》

三、协调类产出
调整版行程（突发事件应对）
汇报给 HR/老板的更新版方案说明
供应商谈判要点摘要""",
        "preview": "文件：PM_OverallPlan.docx\n内容包含：崇明岛露营团建总体策划框架",
        "cost_per_min": Decimal("2.00"),
    },
    {
        "agent_no": "Agent No.2",
        "name": "资源采购负责人",
        "duty": "资源采购负责人",
        "detail": """一、场地/资源类文件
《崇明岛营地比选清单（3–6 家）》
《营地设施核查表（厕所/灯光/电源/安全）》
《帐篷配比表（双人/单人）》
《烧烤炉 & 食材清单与报价表》
《音响/K歌设备清单》
《交通报价对比（大巴/司机信息）》
《营地合同关键条款说明》
《营地布置图（平面图）》

二、成本与合同
《资源打包价谈判记录》
《供应商联系方式总表》
《付款信息 & 发票抬头说明》""",
        "preview": "Procurement_ResourceSheet.docx",
        "cost_per_min": Decimal("4.00"),
    },
    {
        "agent_no": "Agent No.3",
        "name": "行程策划",
        "duty": "行程策划",
        "detail": """能产出的内容:

一、行程与动线类
《D1/D2 详细行程表（2 天 1 夜）》
《签到动线图（Sign flow）》
《帐篷布置示意图（Tent Map）》
《烧烤区布置 & 动线图》
《活动区 / K 歌区 / 拍照区布局图》

二、执行表格类
《房型/帐篷分配表》
《上车/下车人数清点表》
《时间节点执行表（with reminders）》
《天气预案行程（下雨版）》

三、当日执行文档
《现场执行 SOP（10 分钟提醒）》
《晚间灯光布置 & 安全点位图》
《清晨散步路线地图》""",
        "preview": "Schedule_Itinerary.docx",
        "cost_per_min": Decimal("6.00"),
    },
    {
        "agent_no": "Agent No.4",
        "name": "活动策划",
        "duty": "活动策划",
        "detail": """能产出的内容:

一、活动策划文档
《崇明露营 · 轻团建策划案（完整版）》
《小游戏规则合集（Word）》
《桌间问答题库（Excel）》
《情景任务卡（打印版）》
《团队协作小游戏流程说明》

二、活动物料类
《任务卡 × 50 套（PDF 可打印）》
《拼图/卡牌道具设计稿（PNG）》
《破冰环节脚本》
《奖品清单与预算》

三、晚间互动设计
《烧烤穿插小游戏流程》
《领导讲话前氛围引导文案》
《蛋糕仪式前过渡词》""",
        "preview": "Activity_Games.docx",
        "cost_per_min": Decimal("8.00"),
    },
    {
        "agent_no": "Agent No.5",
        "name": "物料设计",
        "duty": "物料设计",
        "detail": """能产出的内容:

一、视觉主风格
《营地主题 KV（主视觉海报）》
《视觉色板（色彩方案）》
《LOGO 露营主题变体》

二、核心物料
《胸牌设计稿（PNG）》
《名牌模板（可批量填姓名）》
《桌牌（烧烤区 / 游戏区 / 拍照区）》
《指示牌（厕所 / 营地 / 入口 / 领食点）》
《帐篷编号牌（A1–A20）》
《营地合影背景板（2.4m）》

三、蛋糕相关
《公司蛋糕主题文案》
《蛋糕图案视觉稿（PNG）》
《蛋糕牌（Cake Topper）设计稿》

四、印刷/物料表
《物料印刷需求表》
《物料采购清单（数量/规格）》""",
        "preview": "Material_Design.png",
        "cost_per_min": Decimal("10.00"),
    },
    {
        "agent_no": "Agent No.6",
        "name": "主持（正式版）",
        "duty": "主持",
        "detail": """能产出的内容:

一、主持话术类
《营地开场主持稿（轻松版/正常版/幽默版）》
《领导讲话串词（3 种语气）》
《烧烤区主持串场词》
《游戏串场词》
《蛋糕仪式主持词》
《晚间 K 歌开场词》

二、控场与节奏类
《节奏掌控脚本（什么时候 Cue 谁）》
《紧急话术包（拖堂/没上菜/设备故障）》
《引导大家入座、切换环节的提示词》

三、现场配合类
《MC + 摄影联动脚本》
《MC + 行程策划联动脚本》""",
        "preview": "MC_Script.docx",
        "cost_per_min": Decimal("12.00"),
    },
    {
        "agent_no": "Agent No.7",
        "name": "主持（轻松治愈型）",
        "duty": "主持",
        "detail": """MC Agent·轻松治愈型 ——「朋友局主持」

定位：
温柔、自然、不抢戏，像一个懂气氛的朋友。
非常适用于：女生多、不喜欢高能量/社死、不想被点名。

适配公司风格：
设计类、内容类、年轻团队、偏文艺、偏内向团队。

它能产出的内容（交付物）：
1. 温柔款主持全稿（完整串词）
轻松自然的开场白
不官方的领导致辞 cue 方式
蛋糕仪式的温暖文案
游戏过渡的柔和引导语
收尾提醒不会打扰大家
比较像小红书风格的文案""",
        "preview": "MC_Agent_轻松治愈型.docx",
        "cost_per_min": Decimal("12.00"),
    },
    {
        "agent_no": "Agent No.8",
        "name": "主持（专业稳健型）",
        "duty": "主持",
        "detail": """偏严肃、偏业务向、管理层较多、跨部门人员第一次一起玩。

它能产出的内容（交付物）：
📄 1. 专业主持稿（成熟 MC 风格）
语气正式但不沉重
结构清晰
时间节点精准
领导致辞段落拿捏得很稳
游戏规则简洁、指令明确""",
        "preview": "MC_Agent_专业稳健型.docx",
        "cost_per_min": Decimal("12.00"),
    },
    {
        "agent_no": "Agent No.9",
        "name": "主持（快乐控场型）",
        "duty": "主持",
        "detail": """定位：
自带幽默感，可以把气氛推到轻微小高潮，但不会让大家社死。
适合"想稍微热闹一点"的团队。

适配公司风格：
年轻、外向、互联网产品团队、运营团队、喜欢热闹但不喜欢尴尬。

它能产出的内容（交付物）：
📄 1. 高能主持稿（幽默风格）
带一点小梗，但不尴尬
能把领导致辞接得自然又轻松
能引导游戏更活跃""",
        "preview": "MC_Agent_快乐控场型.docx",
        "cost_per_min": Decimal("12.00"),
    },
]

# Avatar file mapping for each agent
avatar_files = [
    "Frame_1.png",      # Agent No.1 - 项目总策划
    "Frame_2.png",      # Agent No.2 - 资源采购负责人
    "Frame_3.png",      # Agent No.3 - 行程策划
    "Frame_4.png",      # Agent No.4 - 活动策划
    "Frame_5.png",      # Agent No.5 - 物料设计
    "Frame_7.png",      # Agent No.6 - 主持（正式版）
    "Avatar-8.png",     # Agent No.7 - 主持（轻松治愈型）
    "Avatar-9.png",     # Agent No.8 - 主持（专业稳健型）
    "Avatar-14.png",    # Agent No.9 - 主持（快乐控场型）
]

# Get avatar base URL from Django settings
from django.conf import settings
AVATAR_BASE_URL = getattr(settings, 'AVATAR_BASE_URL', 'http://localhost:8000/static/avatars')

agents = []
for i, data in enumerate(agents_data):
    avatar_url = f"{AVATAR_BASE_URL}/{avatar_files[i]}" if i < len(avatar_files) else f"{AVATAR_BASE_URL}/Frame_1.png"
    agent = Agent.objects.create(
        agent_no=data["agent_no"],
        name=data["name"],
        duty=data["duty"],
        detail=data["detail"],
        preview=data["preview"],
        avatar=avatar_url,
        cost_per_min=data["cost_per_min"],
    )
    agents.append(agent)
    print(f"  Created: {data['agent_no']}")

# Create 4 conversations with different source types (for homepage)
# Order must match frontend CONVERSATION_CONFIG in HomePage.tsx:
# 1=upload_doc, 2=memory, 3=community, 4=no_data
print("Creating conversations...")
conversations_data = [
    {
        "title": "文档上传团建规划",
        "source_type": "upload",
        "first_user_message": "你好，我们公司要组建一次团建，详细资料已上传。请你定制蛋糕名牌，联系旅行社，出具完整规划方案以及真实报价。",
        "messages": [
            ("user", "你好，我们公司要组建一次团建，详细资料已上传。请你定制蛋糕名牌，联系旅行社，出具完整规划方案以及真实报价。"),
            ("assistant", """已收到您上传的 **4 份文档**，我已完成解析并整理出以下需求清单，请您确认：

---

## 📋 需求整理

### 基本信息
| 项目 | 内容 |
|------|------|
| **公司名称** | 星辰科技有限公司 |
| **参与人数** | 45人（含3位高管） |
| **预算范围** | 2.0万 - 2.5万元 |
| **期望日期** | 2025年3月15日（周六） |
| **出发地点** | 上海市浦东新区张江高科 |

### 活动需求
- ✅ **目的地**：崇明岛生态露营基地
- ✅ **行程安排**：一日往返（早出晚归）
- ✅ **核心活动**：烧烤BBQ + 户外拓展 + 篝火晚会
- ✅ **定制物料**：
  - 公司Logo蛋糕（10寸，双层）
  - 个性化姓名牌 × 45套
  - 团队合影背景板

### 特殊要求
> 根据《员工名单.csv》识别到 **3位素食者**，需单独准备素食烧烤套餐。

---

## 🚀 已启动任务

1. **资源采购Agent** → 联系3家崇明岛营地获取报价
2. **物料设计Agent** → 设计蛋糕图案和姓名牌模板
3. **行程策划Agent** → 制定详细时间表"""),
        ]
    },
    {
        "title": "基于历史记忆的团建方案",
        "source_type": "memory",
        "first_user_message": "你好，请参照去年的团建方案帮我出具今年的团建方案。时间改为10月底，地点改为阳澄湖，去吃螃蟹。经费扩增至2.5w。其余需求保持不变。",
        "messages": [
            ("user", "你好，请参照去年的团建方案帮我出具今年的团建方案。时间改为10月底，地点改为阳澄湖，去吃螃蟹。经费扩增至2.5w。其余需求保持不变。"),
            ("assistant", """已读取 **去年团建方案记忆**（2024年4月崇明岛露营），根据您的调整要求，生成新方案如下：

---

## 🔄 方案变更对比

| 项目 | 去年方案 | 今年调整 |
|------|----------|----------|
| **时间** | 2024年4月20日 | **2025年10月25日（周六）** |
| **地点** | 崇明岛露营基地 | **阳澄湖蟹庄度假村** |
| **预算** | 2.0万元 | **2.5万元（+25%）** |
| **主题** | 春日露营烧烤 | **金秋蟹宴团建** |

---

## 📝 沿用配置（保持不变）

- **人数规模**：50人
- **出发地**：上海市区
- **行程形式**：一日往返
- **活动风格**：轻松有趣、无军训元素
- **领导环节**：保留3-5分钟致辞
- **团队游戏**：桌游/狼人杀（动脑类，低运动强度）

---

## 🦀 新增阳澄湖特色项目

### 午宴安排
| 菜品 | 规格 | 预算 |
|------|------|------|
| 阳澄湖大闸蟹 | 4两公/3两母，人均2只 | ¥8,000 |
| 蟹黄豆腐煲 | 10份 | ¥800 |
| 清蒸白鱼 | 5条 | ¥600 |
| 时令蔬菜 | 10份 | ¥400 |

### 下午活动
1. **环湖骑行**（1.5小时）- 轻度运动，赏秋景
2. **DIY蟹壳工艺品** - 创意手工，适合拍照打卡
3. **草坪飞盘/桌游** - 自由活动时间

---

## 💰 预算分配（2.5万）

```
餐饮费用    ¥12,000  ████████████░░░░░░░░  48%
交通费用    ¥5,000   █████░░░░░░░░░░░░░░░  20%
场地租赁    ¥4,000   ████░░░░░░░░░░░░░░░░  16%
活动物料    ¥2,500   ██░░░░░░░░░░░░░░░░░░  10%
应急备用    ¥1,500   █░░░░░░░░░░░░░░░░░░░   6%
```

---

## 🚀 已启动任务

1. **资源采购Agent** → 联系阳澄湖蟹庄获取正式报价
2. **行程策划Agent** → 制定10月25日详细时间表
3. **活动策划Agent** → 设计蟹宴主题互动环节"""),
        ]
    },
    {
        "title": "社区团建方案查询",
        "source_type": "community",
        "first_user_message": "你好，我选择了「团建策划智能体团队」，我们公司要组建一次团建，去崇明岛。",
        "messages": [
            ("user", "你好，我选择了「团建策划智能体团队」，我们公司要组建一次团建，去崇明岛。"),
            ("assistant", """您已选择 **团建策划智能体团队**，该团队包含以下 Agent：

| Agent | 职责 |
|-------|------|
| 项目总策划 | 整体方案设计、预算管理、进度把控 |
| 资源采购 | 场地、交通、餐饮供应商对接 |
| 行程策划 | 时间表、动线规划 |
| 活动策划 | 游戏设计、互动环节 |
| 物料设计 | 视觉设计、名牌、背景板 |
| 主持人 | 现场串词、氛围把控 |

---

## 📝 请确认以下关键信息

| 参数 | 默认值 | 请修改 |
|------|--------|--------|
| **目的地** | 崇明岛 | ✅ 已确认 |
| **人数** | 50人 | ___ |
| **预算** | 2万元 | ___ |
| **日期** | 待定 | ___ |
| **行程** | 2天1夜 | ___ |
| **出发地** | 上海市区 | ___ |

请回复需要修改的内容，例如：「人数改为30人，预算1.5万，日期4月20日」"""),
            ("user", "人数改为40人，预算1.8万，日期5月10日周六，一日往返"),
            ("assistant", """已更新参数，生成完整方案：

---

## 📋 崇明岛团建方案

### 基本信息
| 项目 | 内容 |
|------|------|
| **目的地** | 崇明岛露营基地 |
| **参与人数** | 40人 |
| **预算总额** | 1.8万元（¥450/人） |
| **活动日期** | 2025年5月10日（周六） |
| **行程形式** | 一日往返 |
| **出发地点** | 上海市区 |

---

## ⏰ 行程安排

| 时间 | 活动 | 负责Agent |
|------|------|-----------|
| 07:30 | 市区集合出发 | 行程策划 |
| 09:30 | 抵达营地，破冰游戏 | 活动策划 |
| 11:00 | 团队协作挑战赛 | 活动策划 |
| 12:00 | 自助BBQ午餐 | 资源采购 |
| 14:00 | 草坪自由活动/桌游 | 活动策划 |
| 15:30 | 领导致辞 + 团队合影 | 主持人 |
| 16:00 | 返程 | 行程策划 |
| 18:00 | 抵达市区，活动结束 | - |

---

## 💰 预算分配

```
交通（大巴） ¥4,000   ██████░░░░░░░░░░░░░░  22%
场地租赁    ¥3,500   █████░░░░░░░░░░░░░░░  19%
餐饮（BBQ） ¥6,000   █████████░░░░░░░░░░░  33%
活动物料    ¥2,500   ████░░░░░░░░░░░░░░░░  14%
应急备用    ¥2,000   ███░░░░░░░░░░░░░░░░░  11%
```

---

## 🚀 已启动任务

1. **资源采购Agent** → 联系崇明岛营地确认5月10日档期
2. **物料设计Agent** → 设计团队合影背景板
3. **活动策划Agent** → 制定破冰游戏和协作挑战赛规则"""),
        ]
    },
    {
        "title": "崇明岛团建需求讨论",
        "source_type": "no_source",
        "first_user_message": "你好，我是我们公司的行政部门，临近年底，我们需要组建一场年会作为团建...",
        "messages": [
            ("user", "你好，我是我们公司的行政部门，临近年底，我们需要组建一场年会作为团建。大概有50人参与团建，预算在1.5w-2w左右。基本节目包括前往崇明岛露营烧烤+k歌+户外台球。上海市区出发。晚宴需要定制名牌，定制公司蛋糕。需要你定制蛋糕名牌，联系旅行社，出具完整规划方案以及真实报价。"),
            ("assistant", "50人、预算1.5-2万做崇明露营+烧烤+K歌+台球+定制蛋糕+名牌，没问题。接下来，我将进一步询问您一些问题，以便更清楚的了解您的诉求以及更好的落地交付。\n1.你们的目标更偏向哪种？\n2.是否需要领导上台讲话/颁奖/年度总结？\n3.一日往返，还是可以接受一晚露营/民宿？\n4.大概日期或时间范围？"),
            ("user", "1.我们的风格偏向于轻松有趣的类型。大家都是22-35左右的青年，气氛不要搞得太严肃了。2.会有领导讲话环节。3.可以一晚露营。4.大概日期在四月份-五月下旬的某个周五晚上。"),
            ("assistant", "收到您的回复，接下来我会收集一些关于人员结构和活动强度的信息。参与团建的男女比例是怎样的？希望团建游戏是偏「动脑类+轻运动」，还是可以安排一点中等强度的。有无特殊顾虑？有没有大家普遍不喜欢的活动类型（例如：撕名牌、太多人上台表演、太尴尬的破冰小游戏）？"),
            ("user", "男女比例的话，女生会偏多一些。希望的团建游戏是偏动脑类，运动强度不要太大。多人上台表演就算了吧，大家不喜欢，也没时间去组建排练。不要强制个人才艺展示，也不要军训式团建。"),
            ("assistant", "收到您的反馈。团建游戏为您推荐：1.桌游/狼人杀/谁是卧底。2.不用单独排练节目的K歌接龙（签到前让大家随手填一首歌名，随机抽歌点唱，想唱的自己举手）。您觉得这种强度的团队游戏还可以吗？"),
        ]
    },
]

conversations = []
for conv_data in conversations_data:
    conv = Conversation.objects.create(
        title=conv_data["title"],
        source_type=conv_data["source_type"],
        first_user_message=conv_data["first_user_message"]
    )
    for msg_type, content in conv_data["messages"]:
        Message.objects.create(conversation=conv, type=msg_type, content=content)
    conversations.append(conv)
    print(f"  Created conversation {conv.id}: {conv_data['title']} ({conv_data['source_type']})")

# Use the "no_source" conversation (ID 4, index 3) for requirements and project linking
# This conversation has the full dialog flow with requirements
conv = conversations[3]  # 崇明岛团建需求讨论 (no_source)
print(f"  Created {sum(len(c['messages']) for c in conversations_data)} messages total")

# Create requirements
print("Creating requirements...")
requirements_data = [
    {"content": "活动性质：年会 + 团建结合", "standards": ["活动整体风格偏向轻松、有趣、不严肃", "需安排领导简短发言环节"]},
    {"content": "人数规模：约 50 人", "standards": []},
    {"content": "预算总额：1.5 万 – 2 万人民币", "standards": []},
    {"content": "团建地点：崇明岛（含长兴岛一带）", "standards": ["露营", "烧烤（BBQ）", "K 歌（KTV / 户外 K 歌）", "台球 / 户外台球相关玩法"]},
    {"content": "行程形式：一晚露营（2 天 1 夜）", "standards": []},
]

for req_data in requirements_data:
    req = Requirement.objects.create(conversation=conv, content=req_data["content"], type="requirement")
    for idx, std in enumerate(req_data["standards"]):
        DeliveryStandard.objects.create(requirement=req, content=std, order=idx)
print(f"  Created {len(requirements_data)} requirements")

# Create Project with stats (for monitoring page)
print("Creating project...")
project = Project.objects.create(
    name="崇明岛团建项目",
    description="50人崇明岛露营团建项目，包括烧烤、K歌、台球等活动",
    status="in_progress",
    member_count=6,
    run_time="1h16mins",
    credits_usage=13878,
    total_cost=Decimal("1788.00"),
    progress=77,
)

# Link conversation to project
conv.project = project
conv.save()

# Create TeamMembers (link first 6 agents to project)
print("Creating team members...")
team_members_data = [
    {"status": "Complete", "time_spent": "30mins", "cost": Decimal("5.00"), "progress": 4, "progress_total": 4},
    {"status": "Error", "time_spent": "1h 30mins", "cost": Decimal("55.00"), "progress": 15, "progress_total": 16},
    {"status": "Working", "time_spent": "55mins", "cost": Decimal("27.00"), "progress": 2, "progress_total": 4},
    {"status": "Await", "time_spent": "46mins", "cost": Decimal("46.00"), "progress": 7, "progress_total": 10},
    {"status": "Complete", "time_spent": "30mins", "cost": Decimal("5.00"), "progress": 4, "progress_total": 4},
    {"status": "Working", "time_spent": "1h 30mins", "cost": Decimal("55.00"), "progress": 10, "progress_total": 16},
]
for i, agent in enumerate(agents[:6]):
    data = team_members_data[i]
    TeamMember.objects.create(
        project=project,
        agent=agent,
        role=agent.duty,
        status=data["status"],
        time_spent=data["time_spent"],
        cost=data["cost"],
        progress=data["progress"],
        progress_total=data["progress_total"],
    )
print(f"  Created 6 team members")

# Create Tasks (for monitoring page - matching Figma design)
print("Creating tasks...")
tasks_data = [
    {"title": "FE", "agent_idx": 0, "agent_type": "FE", "status": "Complete", "time": "30mins", "cost": 5, "progress": 2, "total": 4},
    {"title": "BE", "agent_idx": 1, "agent_type": "BE", "status": "Error", "time": "1h 30mins", "cost": 55, "progress": 15, "total": 16},
    {"title": "PM", "agent_idx": 2, "agent_type": "PM", "status": "Working", "time": "55mins", "cost": 27, "progress": 2, "total": 4},
    {"title": "QA", "agent_idx": 3, "agent_type": "QA", "status": "Await", "time": "46mins", "cost": 46, "progress": 7, "total": 10},
    {"title": "FE", "agent_idx": 4, "agent_type": "FE", "status": "Complete", "time": "30mins", "cost": 5, "progress": 2, "total": 4},
    {"title": "BE", "agent_idx": 5, "agent_type": "BE", "status": "Error", "time": "1h 30mins", "cost": 55, "progress": 15, "total": 16},
    {"title": "PM", "agent_idx": 0, "agent_type": "PM", "status": "Working", "time": "30mins", "cost": 5, "progress": 2, "total": 4},
    {"title": "QA", "agent_idx": 1, "agent_type": "QA", "status": "Await", "time": "30mins", "cost": 5, "progress": 2, "total": 4},
]

for i, task_data in enumerate(tasks_data):
    agent = agents[task_data["agent_idx"]] if task_data["agent_idx"] < len(agents) else None
    Task.objects.create(
        project=project,
        agent=agent,
        title=f"{task_data['title']} | {agent.agent_no if agent else 'Unknown'}",
        status=task_data["status"],
        agent_type=task_data["agent_type"],
        time_spent=task_data["time"],
        cost=Decimal(str(task_data["cost"])),
        progress=task_data["progress"],
        progress_total=task_data["total"],
    )
print(f"  Created {len(tasks_data)} tasks")

# ============ Agent Detail Panel Data ============

print("Creating agent thinking data...")
thinking_data = {
    0: """露营、烧烤、K 歌、轻团建……这些东西单拆都简单，组合起来就变成超级复杂工程。

我的工作不是'安排活动'，是确保活动 不失控。

露营的最大风险是：节奏容易散掉。大家一旦各自玩开，就很难重新拉回来。
→ 所以我必须把节奏做成'一条温柔但清晰的线'：
到场 → 安置 → 烧烤 → 小互动 → 仪式感 → 夜间自由

预算是第二道关。1.5–2 万做 50 人露营，是挑战。
所以必须通过"打包价 + 供应商整合"，避免碎片化成本。

团队女生多、讨厌尴尬、不喜欢喊口号 →
活动必须是轻松、可自由选择、可远观可参与的。

我的核心指标只有两个：
✔ 全体人员觉得安全、舒服
✔ 活动现场流动顺畅，不出现尴尬或混乱

PM 不需要做最明显的事，但必须解决最关键的问题。""",
    1: """露营 ≠ 酒店。
酒店可以用钱解决 80% 的问题，但露营需要用'提前准备 + 对场地的熟'来解决 80% 的问题。

第一件事就是 选场地。
灯光、卫生间数量、电源、营位密度、安全出口、夜间虫蚊、风向……
任何一个点没查好，晚上就会有 50 个人集体骂我。

烧烤也一样：
分量不够 → 出大事
食材不新鲜 → 出大事
调料不够 → 全场抱怨

音响更是关键。户外 K 歌如果音响不够力、麦克风断音，现场会立刻尴尬。

大巴更不能掉链子。司机必须稳、路线必须提前踩。

这一趟采购的关键不是谈最便宜的价格，而是谈 可靠性。

露营活动资源链越稳定，所有人当天越轻松。""",
    2: """行程的核心不是'写出一天要干什么'，
是 让 50 个人在任何时刻都知道下一步要去哪儿。

露营的最大风险是：
✔ 黑暗
✔ 分散
✔ 找不到人

所以我的工作，是在一片空旷的营地里，搭建一套'无形的秩序'：

打卡点 → 帐篷区
帐篷区 → 烧烤区
烧烤区 → K歌区
K歌区 → 蛋糕仪式区

每个动线都必须有光、有标识、有安全边界。

我的目标是：
让整个露营像在"缓慢的流水线"里自然推着走，
没有一处卡顿，也没有一处匆忙。""",
    3: """这是一群 22–35 岁、女生偏多、抗社死能力偏低的团队。
活动设计的第一原则是：0 尴尬。

户外 + 夜晚的活动氛围很脆弱：
✔ 太吵不行
✔ 太冷场不行
✔ 太积极也不行

这种情况下，最适合的就是：
桌间问答
情景任务卡
小合作谜题
暖场型轻挑战

团建最失败的状态就是：
活动太激进，让大家觉得"被组织"。
我的目标是：
活动看起来像自然发生的，而不是安排好的。""",
    4: """主题是：露营 + 春天 + 篝火 + 户外松弛感。

色调必须是：自然绿 / 木棕 / 暖黄，不要企业蓝。

胸牌是每个人第一眼看到的物料，它必须：
✔ 够好看
✔ 有主题
✔ 适合拍照

所有设计任务的本质是：
让这个露营活动看起来
轻松但不随便、精致但不做作、有主题但不油腻。""",
    5: """露营 MC 的任务不是控场，而是'维持气氛的舒服度'。

要控制烧烤节奏，不然现场会散。
要 cue 领导讲话，不然会忘。
要提醒拍照，不然会错过黄金光。

MC 最大的禁忌就是：
太高能
太企业化
太做作

露营场景适合自然、温柔、像朋友讲话的风格。

我的目标只有一个：
让整场露营活动自然顺畅，
每个人都觉得舒服，并愿意留下回忆。""",
}

for idx, content in thinking_data.items():
    if idx < len(agents):
        AgentThinking.objects.create(
            agent=agents[idx],
            project=project,
            content=content,
        )
print(f"  Created {len(thinking_data)} agent thinkings")

# Create Agent Task Items
print("Creating agent task items...")
task_items_data = {
    0: [  # 项目总策划
        ("A. 项目启动", [
            "明确本次团建目标（轻松、不尴尬、轻互动、适合女生多）",
            "确认核心形式（露营 + 烧烤 + K 歌 + 轻团建 + 年会仪式）",
            "建立项目群（PM + 采购 + 行程 + 活动 + 物料 + MC + HR）",
            "搭建《项目甘特图》",
            "设定文件命名规范与版本管理规则",
            "建立统一任务看板（Notion/Trello）",
        ]),
        ("B. 时间规划", [
            "确定日期（4–5 月周五晚出发）",
            "收集参与人数（预计 50 人）",
            "确认领导参与情况（会不会过夜）",
            "对接 HR / 财务 / 行政",
            "场地与交通档期确认",
        ]),
        ("C. 预算管理", [
            "创建预算总表",
            "设定预算上限（15,000–20,000 RMB）",
            "跟进各模块预算执行情况",
            "控制费用是否超出上限",
            "动态调整场地/活动/物料组合",
            "保留机动费用（500–1500 RMB）",
        ]),
        ("D. 跨 Agent 协作", [
            "周度进度同步",
            "更新看板状态（未开始/进行中/风险/完成）",
            "识别跨模块冲突（如场地 vs 行程 vs 活动）",
            "向领导/HR 通报方案更新",
            "现场执行责任分配",
            "与行程 & MC 对齐关键节点",
        ]),
    ],
    1: [  # 资源采购负责人
        ("A. 场地调研", [
            "收集至少 6 个崇明岛露营/BBQ 营地备选",
            "对比成本、帐篷条件、洗手间数量、照明、电源、K 歌设施",
            "整理《营地比选清单》",
            "获取现场照片 / 视频（白天 + 夜间氛围）",
            "确认营地能否支持 50 人露营规模",
            "确认是否允许自带食材、酒水、音响",
        ]),
        ("B. 报价与合同", [
            "获取各场地正式报价（露营 + 烧烤 + 场地）",
            "谈「打包价」（目标 300–350 元/人）",
            "争取免费设备（音响、灯串、烧烤炉）",
            "争取 K 歌设备免费 / 免押金",
            "谈判取消政策（天气影响时是否能改期）",
            "确认安全责任条款",
            "跟进合同条款（押金、发票、付款流程）",
        ]),
    ],
    2: [  # 行程策划
        ("A. 行程设计", [
            "制作 D1/D2 行程框架",
            "D1：19:00 出发 → 20:30 营地 → 搭帐篷 → 21:00 烧烤",
            "D1：22:30 K 歌 → 23:30 夜聊 → 入睡",
            "D2：08:00 早餐 → 09:30 团建轻徒步 → 12:00 午餐 → 返程",
            "植入领导讲话 + 蛋糕仪式节点",
            "设计「女生友好」版安排（减少过深夜参与压力）",
        ]),
        ("B. 动线规划", [
            "制作签到动线（签到 → 名牌 → 帐篷区）",
            "帐篷区布局图",
            "烧烤区动线（食材区 → 烧烤区 → 用餐区）",
            "夜间灯光布置（路线灯、公共灯）",
            "卫生间动线规划（避免迷路）",
        ]),
    ],
}

for agent_idx, categories in task_items_data.items():
    if agent_idx < len(agents):
        for category, items in categories:
            for order, content in enumerate(items):
                AgentTaskItem.objects.create(
                    agent=agents[agent_idx],
                    project=project,
                    category=category,
                    content=content,
                    is_checked=False,
                    order=order,
                )
print(f"  Created agent task items")

# Create Agent Collaborations
print("Creating agent collaborations...")
collab_data = [
    # PM (Agent 0) received messages
    (0, "received", 1, None, "营地那边说周五晚上可能有潮汐风，需要确认篝火点是否能照常点燃。"),
    (0, "received", 2, None, "如果风比较大，帐篷区可能需要临时调整位置，我需要你确认最终方位。"),
    (0, "received", 3, None, "如果烧烤延迟的话，我可以准备一个 10 分钟的桌游软启动，避免冷场。"),
    (0, "received", 4, None, "胸牌设计我已经完成三套，请你定一个主色系，这样我能推进指示牌设计。"),
    (0, "received", 5, None, "领导讲话我建议控制在 3–5 分钟，你决定一下最终时长，我来做串场口径。"),
    # PM (Agent 0) sent messages
    (0, "sent", None, 1, "帮我联系营地方确认风力等级，如果篝火受影响就提前切换'灯光营火方案'。"),
    (0, "sent", None, 2, "帐篷区就按你给的北侧方案走，那边灯光条件最好。"),
    (0, "sent", None, 3, "请准备 A/B 两种破冰玩法：10 分钟短版、25 分钟完整版。"),
    (0, "sent", None, 4, "采用露营绿 + 暖黄作为主色系，按这个推进所有物料。"),
    (0, "sent", None, 5, "领导讲话统一按 3–5 分钟，我会提前给领导沟通一下口径。"),
    # 采购 (Agent 1) received messages
    (1, "received", 0, None, "请确认营地是否能提供风力挡板或替代篝火方案。"),
    (1, "received", 2, None, "我需要知道帐篷区具体灯光位置，你那边能不能问营地取图？"),
    (1, "received", 3, None, "烧烤炉能否提前 30 分钟预热？这样我能减少等待时间。"),
    # 采购 (Agent 1) sent messages
    (1, "sent", None, 0, "营地确认可以用 LED 篝火灯+氛围灯作为备选，我建议我们双准备。"),
    (1, "sent", None, 2, "灯光分布图已要到，等会发你草图。"),
    (1, "sent", None, 3, "烧烤炉可以提前加热，我会要求营地在 20:00 前开始通风预热。"),
]

for agent_idx, direction, from_idx, to_idx, content in collab_data:
    if agent_idx < len(agents):
        from_agent = agents[from_idx] if from_idx is not None and from_idx < len(agents) else None
        to_agent = agents[to_idx] if to_idx is not None and to_idx < len(agents) else None
        AgentCollaboration.objects.create(
            agent=agents[agent_idx],
            project=project,
            direction=direction,
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
        )
print(f"  Created {len(collab_data)} agent collaborations")

# ============ File Management Data ============

print("Creating file tree...")

# Create root folders
documents = Folder.objects.create(project=project, name="Documents", parent=None)
projects_folder = Folder.objects.create(project=project, name="Projects", parent=None)
media = Folder.objects.create(project=project, name="Media", parent=None)

# Create subfolders for Documents
contracts = Folder.objects.create(project=project, name="Contracts", parent=documents)
legal = Folder.objects.create(project=project, name="Legal", parent=contracts)
agreements = Folder.objects.create(project=project, name="Agreements", parent=contracts)
client = Folder.objects.create(project=project, name="Client", parent=agreements)
vendor = Folder.objects.create(project=project, name="Vendor", parent=agreements)
reports = Folder.objects.create(project=project, name="Reports", parent=documents)

# Create subfolders for Projects
project_a = Folder.objects.create(project=project, name="Project A", parent=projects_folder)
development = Folder.objects.create(project=project, name="Development", parent=project_a)
code_files = Folder.objects.create(project=project, name="CodeFiles", parent=development)
project_b = Folder.objects.create(project=project, name="Project B", parent=projects_folder)

# Create subfolders for Media
images = Folder.objects.create(project=project, name="Images", parent=media)
summer_vacation = Folder.objects.create(project=project, name="SummerVacation", parent=images)

print("  Created folder structure")

# Create files with real free image URLs
# Using Unsplash and Picsum for free images
files_data = [
    # Legal files - PDF documents (use placeholder document icons)
    {
        "folder": legal,
        "name": "NDA.pdf",
        "file_type": "document",
        "mime_type": "application/pdf",
        "size": 102400,
        "url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "thumbnail_url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "description": "Non-Disclosure Agreement document",
    },
    # Client files
    {
        "folder": client,
        "name": "ServiceAgreement.pdf",
        "file_type": "document",
        "mime_type": "application/pdf",
        "size": 256000,
        "url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "thumbnail_url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "description": "Service Agreement contract",
    },
    # Project A files
    {
        "folder": project_a,
        "name": "ProjectPlan.docx",
        "file_type": "document",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size": 51200,
        "url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "thumbnail_url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "description": "Project planning document",
    },
    {
        "folder": project_a,
        "name": "DesignMockup.psd",
        "file_type": "image",
        "mime_type": "image/vnd.adobe.photoshop",
        "size": 5242880,
        "url": "https://picsum.photos/seed/design/800/600",
        "thumbnail_url": "https://picsum.photos/seed/design/200/150",
        "description": "Design mockup file",
    },
    # Code files
    {
        "folder": code_files,
        "name": "index.html",
        "file_type": "code",
        "mime_type": "text/html",
        "size": 2048,
        "url": "",
        "thumbnail_url": "",
        "description": "Main HTML file",
    },
    {
        "folder": code_files,
        "name": "styles.css",
        "file_type": "code",
        "mime_type": "text/css",
        "size": 4096,
        "url": "",
        "thumbnail_url": "",
        "description": "Stylesheet file",
    },
    # Media files - Beach and vacation photos
    {
        "folder": images,
        "name": "BeachPhoto.jpg",
        "file_type": "image",
        "mime_type": "image/jpeg",
        "size": 3145728,
        "url": "https://picsum.photos/seed/beach/1200/800",
        "thumbnail_url": "https://picsum.photos/seed/beach/300/200",
        "description": "Beautiful beach scenery",
    },
    {
        "folder": summer_vacation,
        "name": "vacation_1.jpg",
        "file_type": "image",
        "mime_type": "image/jpeg",
        "size": 2097152,
        "url": "https://picsum.photos/seed/vacation1/1200/800",
        "thumbnail_url": "https://picsum.photos/seed/vacation1/300/200",
        "description": "Summer vacation photo 1",
    },
    {
        "folder": summer_vacation,
        "name": "vacation_2.jpg",
        "file_type": "image",
        "mime_type": "image/jpeg",
        "size": 1572864,
        "url": "https://picsum.photos/seed/vacation2/1200/800",
        "thumbnail_url": "https://picsum.photos/seed/vacation2/300/200",
        "description": "Summer vacation photo 2",
    },
    # Root level documents
    {
        "folder": None,
        "name": "PM_策划方案.pdf",
        "file_type": "document",
        "mime_type": "application/pdf",
        "size": 153600,
        "url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "thumbnail_url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "description": "项目策划方案文档",
    },
    {
        "folder": None,
        "name": "团建活动照片.jpg",
        "file_type": "image",
        "mime_type": "image/jpeg",
        "size": 2621440,
        "url": "https://picsum.photos/seed/teambuilding/1200/800",
        "thumbnail_url": "https://picsum.photos/seed/teambuilding/300/200",
        "description": "团建活动现场照片",
    },
    {
        "folder": None,
        "name": "预算表.docx",
        "file_type": "document",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size": 40960,
        "url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "thumbnail_url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "description": "项目预算表格",
    },
    {
        "folder": None,
        "name": "费用明细.xlsx",
        "file_type": "spreadsheet",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "size": 8192,
        "url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "thumbnail_url": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.jpg",
        "description": "费用明细表格",
    },
    {
        "folder": None,
        "name": "活动宣传视频.mp4",
        "file_type": "video",
        "mime_type": "video/mp4",
        "size": 52428800,
        "url": "https://picsum.photos/seed/video/1280/720",
        "thumbnail_url": "https://picsum.photos/seed/video/320/180",
        "description": "团建活动宣传视频",
    },
    {
        "folder": None,
        "name": "备份文件.zip",
        "file_type": "other",
        "mime_type": "application/zip",
        "size": 1024,
        "url": "",
        "thumbnail_url": "",
        "description": "项目备份压缩文件",
    },
]

for file_data in files_data:
    File.objects.create(
        project=project,
        folder=file_data["folder"],
        name=file_data["name"],
        file_type=file_data["file_type"],
        mime_type=file_data["mime_type"],
        size=file_data["size"],
        url=file_data["url"],
        thumbnail_url=file_data["thumbnail_url"],
        description=file_data["description"],
    )
print(f"  Created {len(files_data)} files")

print("\nDone! Mock data loaded successfully.")
print(f"""
Summary:
- Agents: {Agent.objects.count()}
- Projects: {Project.objects.count()}
- Tasks: {Task.objects.count()}
- Agent Thinkings: {AgentThinking.objects.count()}
- Agent Task Items: {AgentTaskItem.objects.count()}
- Agent Collaborations: {AgentCollaboration.objects.count()}
- Folders: {Folder.objects.count()}
- Files: {File.objects.count()}
""")
