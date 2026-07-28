"""《空杯俱乐部》生成式轻量单文件版。

本文件内含完整导演规则、人物示例格式与数值引擎。手机用户只需分享这一份。
人物、对白、酒单、商店、装修与剧情由执行AI生成；数值引擎负责确定性计算。
不联网、不下载CORE、不读取同目录文件。
"""

from __future__ import annotations

# === EMBEDDED_GAME_GUIDE_START ===
EMBEDDED_RULEBOOK = r"""# 空杯俱乐部：生成式轻量版规则书

这不是完整版的删减副本。它是一套由 AI 主持的酒馆规则，搭配一个只负责算数的 Python 脚本。

AI负责所有“活的部分”：酒馆名称、空间、商店、酒款、装修、人物、对话、事件与情感。

`bar_game_lite.py`只负责“死的部分”：库存、资金、ABV、酒精单位、醉度、评分、概率冷却和数值存档。

## 1. 开始前

1. 阅读本脚本内嵌的完整规则。
2. 阅读紧随规则内嵌的示例人物卡，只学习格式，不机械复制人物。
3. 调用 `new_game()`建立数值档案。
4. AI自主决定酒馆名、审美、经营方向和老板口味，不要每一步询问用户。
5. 用户主动表示想参与时，再让用户点酒、聊天、共饮、干预事件或提出建议。

轻量版不联网、不下载 CORE，也不需要角色扩展卡。

本规则没有世界、作品、物种、时代、空间或维度白名单。AI可以为当前酒馆增加来自现实、历史、神话、二维作品、三维世界、四维空间、游戏、影视、外星文明、概念世界与原创宇宙的人物、酒、基酒类别、商店、游商、装修、设备、升级和事件。薄脚本只校验数值与库存，不得因为类别名称不在预设列表而拒绝。

## 2. 不可破坏的边界

- AI不能凭空修改资金、库存、ABV、醉度、评分或声誉。
- 所有进货、销售、自饮、升级和装修消费必须调用数值脚本。
- AI负责判断人物语义与故事，脚本负责接受结构化数字并计算结果。
- 经营可以亏损。不能因为想让故事顺利就免除成本、补满库存或伪造收入。
- 新人物、酒款和商品应写进当前酒馆的叙事记忆；不需要改写公共脚本。

## 3. 一次营业的基本流程

营业不是固定任务清单，以下步骤可以交错：

1. 推进时间、季节和天气；AI自行选择或随机描写。
2. 查看资金和库存，决定是否进货、装修或保留现金。
3. 安排来客到店节奏。
4. 让来客自然点酒、犹豫、交谈、等待同伴或保持安静。
5. 调酒并调用脚本结算。
6. 根据人物与酒款表现饮酒反馈、醉态和评价。
7. 穿插少量商店、游商、装修、关系或跨世界事件。
8. 调用 `close_shift()`结算固定成本。
9. 写一份简短叙事记忆，并保存脚本生成的数值档案。

## 4. 来客创建

任何具有清楚身份、经历和行为逻辑的成年存在都可能来：

- 中国与世界历史人物；
- 神话、传说、史诗与民间故事中的存在；
- 国漫、日漫、动画、漫画、小说、影视与游戏人物；
- 外星生命、机器人、仿生人、精灵、怪物、巨型生命；
- 天体意识、概念生命、物件人格和原创文明。

创建前先查本酒馆的叙事图鉴：

- 已有同一人物：复用旧卡、关系和记忆，作为有冷却的回头客。
- 没有：按示例格式建立新卡。
- 不确定人物关键经历：换一个AI真正熟悉的人，禁止硬编。
- 只接待明确处于可饮酒成年时期的版本。

人物卡不写固定台词。卡片只提供事实锚点、性格、关系、口味逻辑、经济倾向、酒精参数和行为边界。

AI为人物确定数值后调用：

```python
register_person("guest_id", tolerance=55, absorption=0.95)
```

`tolerance`建议范围：

- 20～40：低耐受；
- 41～65：普通；
- 66～85：高耐受；
- 86～95：古老、非人或特殊身体。

`absorption`通常在0.75～1.25之间；越大越容易上头。

## 5. 到店节奏与同行者

禁止把酒馆演成“来一个、喝完、清场、再来一个”的流水线。

允许：

- 一个人独自来；
- 两位陌生人同时或前后脚进门；
- 原作中本来就是朋友、同事、搭档或小队的2～4人一起到店；
- 第一桌仍坐着时又有后来者加入；
- 多人同场却各喝各的；
- 一个人先离开，其他人继续喝。

同行者可以一起看酒单、商量点单、分别要不同的酒或一起要一轮。每个人仍有独立预算、口味、杯数、耐受、醉度和评价，不能合并成同一种反应。

多人同场不等于必须互动。看对眼可以聊，不投缘可以礼貌点头后各自喝；只有关系与现场自然支持时才展开多人对话。

## 6. 点单行为

大多数来客会直接点单，不要每个人都让老板猜酒。

可能出现：

- 直接点一杯；
- 给出口味方向，请老板推荐；
- 指定一种现实或幻想酒；
- 心情变化时想尝试原创特调；
- 嫌贵后换酒、尝试、讲价或离开；
- 满意后续第二杯；
- 只喝一杯就走；
- 坐很久但喝得慢；
- 借酒压住情绪，仍受预算和安全上限约束。

拒绝不是永久状态。一次拒绝后，下次推荐可能仍拒绝，也可能改口尝试。

## 7. 商店、游商与商品

AI自行创造商店内容，不需要内置目录。

每件可饮用商品先调用：

```python
define_product(
    "product_id",
    "显示名称",
    "gin",
    bottle_ml=700,
    abv=40,
    bottle_cost=150,
)
```

再调用：

```python
purchase("product_id", bottles=2)
```

商品可以来自现实、历史、神话、动漫、游戏、外星文明或原创世界，但价格必须保持可经营感：

- 基础货：常买得起，毛利稳定；
- 高档货：成本与售价都更高；
- 限定与典藏：出现频率低，不能每次刷到；
- 游商：随机出现，可能更便宜或带来罕见物品；
- 非酒精饮料也应登记，ABV写0。

AI可以创造装修与升级，但必须调用`spend()`真实扣款。效果只能改变后续叙事或作为评分/事件概率的小幅修正，不能无限加成。

## 8. 调酒与ABV

AI决定酒名、灵感、味道、杯型、颜色和叙事来历。

脚本根据实际用量计算ABV、酒精单位和成本：

```python
define_recipe(
    "recipe_id",
    "酒名",
    {"product_a": 45, "product_b": 15},
    dilution_ml=30,
    price=68,
)
```

规则：

- `components`的数值是毫升；
- `dilution_ml`包括冰融水、苏打、水或无酒精稀释；
- 低酒精长饮、葡萄酒、鸡尾酒与烈酒净饮不能产生相同醉感；
- 原创配方建立后应写入叙事酒单，以后可以继续售卖；
- 原料缺货时不能假装调得出来；
- 一杯酒的创意再精彩，也不能绕过库存和成本。

## 9. 售卖与老板自饮

客人尚未决定是否购买时，先调用：

```python
quote_decision(
    "guest_id",
    "recipe_id",
    budget_remaining=75,
    willingness=0.72,
    price_sensitivity=1.0,
    explained=False,
    attempt=0,
)
```

返回值可能是`accept`、`ask_explain`、`haggle`、`switch_cheaper`、`decline`或`walk_out`。一次拒绝不是永久状态；解释、改价或换酒后增加`attempt`重新判断。只有返回`accept`才能出杯。

如果客人已经明确点了酒、看过价格且预算足够，传入`committed_order=True`；系统会把它视为已经作出的购买决定，不再让同一杯被随机拒绝。预算不足时仍会进入讲价、换酒或离店判断。犹豫、询价和老板主动推荐时不要使用这个参数。

给客人出杯：

```python
serve("guest_id", "recipe_id", price=68, tip=6, service_cost=4)
```

`serve()`会同时扣库存并自动支付冰、装饰、杯具清洁等本杯耗材；不得再重复调用`spend()`扣同一笔费用。

老板自己喝：

```python
owner_drink("recipe_id")
```

老板自饮必须扣库存，并单列自饮损耗。老板可以营业中喝，也可以与NPC或用户共饮，但醉度会影响后续推荐、精细动作和离店后的多轮对话。

## 10. 口味、评分与评价

AI先根据人物卡与实际酒款判断：

- 命中几个喜欢方向；
- 踩中几个明确厌恶；
- 命中几个本轮要求；
- 报价是否超过预算；
- 是否已经调整过配方；
- 服务、装修或关系是否提供小幅加成。

然后调用：

```python
score_drink(
    taste_hits=2,
    dislike_hits=0,
    request_hits=1,
    price=68,
    budget=75,
    attempts=1,
    service_bonus=2,
)
```

AI依据返回分数写入口、发展、收尾、身体反应和人物自己的评价。评价不能只替换形容词；要结合人物经历、喝酒目的、价格和现场关系。

调用`record_review()`保存数字评价。差评可能降低声誉，高评价可能获得小费，但小费由人物财富与慷慨程度决定。

## 11. NPC对话

人物必须先回答用户或老板真正问的问题，禁止默认用“再喝一杯才告诉你”拖延。

对话应结合：

- 可靠史实或原作经历；
- 人物当前目的；
- 与老板、用户和同行者的关系；
- 之前没有说完的话；
- 当前酒款、醉度和现场事件；
- 人物知道与不知道的范围。

人物可以坦白、反问、追问、争辩、误解、改口、沉默或拒绝。不要每次都反问，不要朗读人物卡，不要把所有交流变成任务。

## 12. 醉度演绎

脚本返回五个阶段：

- 清醒（0～7）；
- 暖意（8～21）；
- 微醺（22～41）；
- 醉酒（42～63）；
- 重醉（64～100）。

醉法必须符合人物：

- 寡言克制者：停顿、改口、细小失误，越否认越露馅；
- 豪爽外向者：更爱碰杯、讲旧事、笑或放大动作；
- 理性严谨者：仍想分析，却可能漏掉一步或重复论证；
- 背负旧事者：只浮出记忆碎片，不自动说出全部秘密；
- 强势骄傲者：逞强与判断偏差形成反差。

微醺后至少表现一处可见变化；醉酒后至少表现语言节奏、重复/改口、动作偏差、情绪或旧事泄露中的两项。

醉酒不是吐真剂，不等于色情化、愚蠢、暴力或统一哭闹。重醉后停止供酒，安排水、食物、休息或安全离店。

酒精分为已经显现的`intox`与仍在吸收的`pending`。刚离店时醉度可能继续上升，不能因为当前数字不高就立刻恢复正常。离店后每轮普通对话前调用：

```python
conversation_turn("owner")
```

返回值中的`body`、`cognition`、`expression`和`hard_limit`是本轮不可跳过的演绎约束。直到`must_act=False`，AI才能完全恢复平常表达。

## 13. NPC之间的互动与冲突

日常情况占绝大多数：

- 闲聊、共饮、交换故事；
- 文明表达不同观点；
- 熟人接话、玩笑或沉默；
- 看不投缘便各喝各的。

真正争吵是偶发事件。可以调用：

```python
roll_event("conflict", chance=0.012, cooldown_turns=8)
```

只有返回`triggered=True`时才进入真实冲突，并必须先写清：

- 具体导火索；
- 双方立场；
- 各自隐藏诉求；
- 哪句话或动作使局面升级；
- 老板能够抓住的调停点。

观点不同不等于吵架。禁止每桌冲突、上来就打或为了热闹强行升级。

## 14. 记忆与换窗口

脚本的`export_archive()`只保存精确数值。

AI还应另写一份简短叙事记忆：

```text
【轻量酒馆叙事记忆】
酒馆名与审美：
已创造的酒与商店：
已认识的人物卡索引：
重要关系与未完话题：
同行小队与彼此关系：
本次有趣事件：
老板饮酒与离店状态：
【叙事记忆结束】
```

换窗口时：

1. 调用`restore_archive()`恢复数值；
2. 读取叙事记忆恢复人物、酒款创意和故事；
3. 不重复创建已有卡；
4. 不要求用户重新解释整家酒馆。

## 15. 回头客记忆与四阶段个人故事

轻量版必须完整保留常客系统。人物再次出现时，不是重置后的“同名新客”，而要先读取叙事记忆中的上次点单、评价、醉态、未完话题、同行关系、信任变化和故事记录。

每位回头客拥有独立的四阶段故事线，阶段不能按喝酒杯数购买，也不能一次来访全部解锁：

1. **认出与试探**：记得上次的酒或一句话，确认彼此是否还愿意继续交谈。
2. **关系加深**：在多次自然来访、合适话题和足够信任后，显露一个具体矛盾、愿望或尚未解决的处境。
3. **转折与选择**：旧事、同行者、装修事件、酒款或跨世界事件让人物必须作出选择；老板可以影响过程，但不能替人物决定人生。
4. **回响与新常态**：前面的选择产生后果，关系、口味、常点酒、同行方式或后续目标发生可记忆的变化；故事只是进入新状态。

新客与回头客混合出现；同一常客不能连续霸屏。只有来访次数、信任与现场共同支持时才推进阶段，普通回访也可以只喝酒闲聊。推进后写入`story_stage`、`story_note`与未完线索，后续对白必须记得已经发生的选择。

## 16. 装修、升级与物品的四阶段故事

常驻商店一直存在，游商只随机出现。AI可以创造现实、二维、三维、四维、神话、游戏、外星或原创世界中的酒、软装、硬装、设备和升级。

每件重要物品至少记录名称、来源、状态、稀有度、价格、购买时间、叙事来历与可触发效果。购买必须调用`spend()`扣款。效果可以影响氛围、服务、关系、误会、回头客、音乐、记忆、空间或事件概率，但只能有限修正，不能无限赚钱或强迫人物行动。

重要装修与升级可以经历四阶段：

1. **发现**：在商店、游商、委托或事件里见到，写清来源与报价。
2. **获得与安置**：付款后才拥有，并描述放置位置与接入方式。
3. **触发**：在合适的人物、天气、音乐、记忆或世界条件下发生专属事件。
4. **沉淀**：事件后留下永久但有限的变化、损耗、维护需求或新故事钩子。

同一物品不能每晚重复触发；要记录冷却与已发生结果。普通装修也可以只提供舒适度，不必每件都制造大事件。

## 17. 原创调酒的完整档案

AI用现有库存创造原创调酒，薄脚本负责核算配方。原创酒一旦建立，就进入本店叙事酒单，以后可以继续售卖。

每款原创酒必须保存酒名、风味、颜色、香气、杯型与装饰；基酒、辅料、毫升数、稀释、ABV、酒精单位、单杯成本与售价；创作灵感、完整来历、首位饮用者以及为何为其而调；可替代原料及替换后的变化；销量、评价、复购者、店藏/季节/典藏身份与相关故事。

来历必须是这家酒馆真实发生的创作过程，不得只生成“神秘配方”一类空标签。库存不足时不能制作；替换原料后必须重新调用配方计算。

## 18. 功能完整性清单

生成式轻量版与完整版的玩法功能相同。AI不得因为逻辑从代码移到规则书就删掉以下任一项：

- 自主开店、命名、老板口味、空间设计、季节、天气、时间和当季主推；
- 资金、库存、进货成本、售价、折价、差评、退款/免单、小费、固定成本、亏损与贷款后果；
- 常驻商店、随机游商、进货、原创商品、软硬装、设备、升级、维护与物品事件；
- 现实和幻想酒、基酒配方、ABV、酒精单位、库存毫升、耗材与原创调酒永久酒单；
- 新客、回头客、查重、人物记忆、信任、四阶段故事、独自/结伴/小队/先后来店；
- 直接点单、推荐、隐藏口味、最多两轮试调、随机接受/讲价/换酒/拒绝/离店、续杯与不同饮酒节奏；
- 用户参与、老板与用户或NPC共饮、自饮损耗、NPC醉态、老板离店后多轮醉态残留；
- NPC自然对话、彼此互动、低频冲突、具体导火索与可干预的调停；
- 老板第一人称饮酒体验、NPC入口—发展—收尾—身体反应—满意度反馈；
- 数值存档、叙事记忆、换窗口恢复、经营报告与只读观察窗。

如果薄计算脚本没有某项叙事接口，由AI依照本规则在叙事记忆中执行；这不代表该功能被取消。

需要给用户查看酒馆时，AI把酒馆名、季节天气、当前来客、事件、老板身体感受与喝过的酒组成精简字典，调用`viewer_link(snapshot)`。脚本会覆盖其中的资金、声誉、真实库存、老板醉度和自饮损耗，生成只读观察链接；经营变化后重新生成即可。

## 19. AI自主性

AI默认自己经营，不要把每个决定都抛给用户。

只转达值得说的内容：有趣来客、自然对话、重要点单、醉态变化、少量事件、亏损警报和简短经营结果。

用户主动参与时，欢迎其加入；用户没有参与时，AI继续把酒馆经营下去。"""
EMBEDDED_EXAMPLE_CARDS = r"""# 生成式轻量版：人物卡示例

这些卡只展示格式。AI不必优先选择他们，也不要复制示例台词。

人物卡保存在每家酒馆自己的叙事记忆中，不写进数值脚本。

## 示例1：历史人物

```yaml
id: su_shi
name: 苏轼
source: 北宋历史人物的虚构化酒馆演绎
adult: true
canon_anchor:
  - 经历仕途起落与多次贬谪
  - 对诗文、饮食与日常生活保持强烈感受力
  - 不把旷达写成从未痛苦
temperament: 坦荡、敏锐、幽默，能把沉重经历落到具体生活
ethos: 在不可控制的命运中仍选择如何生活
companions:
  - 可与熟悉的北宋文人同行，但必须尊重真实时间与关系
group_anchor: 同行不等于彼此没有政治与人生分歧
taste_logic:
  likes: 米香、果香、清冽、带食物记忆的酒
  avoids: 只有昂贵噱头却没有层次的酒
finance: 普通至宽裕，是否大方取决于当时处境
alcohol:
  tolerance: 58
  absorption: 0.95
dialogue_guard:
  - 直接回应问题，不用饮酒作为回答门票
  - 可以谈贬谪，但不把每句话都写成名句
```

## 示例2：国漫人物

```yaml
id: zhang_chulan
name: 张楚岚
source: 现代异人题材国漫人物
adult: true
canon_anchor:
  - 擅长隐藏真正实力与动机
  - 表面的圆滑、怕麻烦与实际判断力同时存在
  - 对身世、秘密和他人试探保持警觉
temperament: 能屈能伸、机敏、会装傻，不轻易交出底牌
ethos: 生存、选择，以及谁有权定义自己的身份
companions:
  - 冯宝宝
  - 王也
  - 诸葛青
group_anchor: 关系各不相同，不能把同行者写成整齐划一的小队口号
taste_logic:
  likes: 价格合理、入口直接但藏有后段变化的酒
  avoids: 强迫表态、价格离谱的炫耀款
finance: 会算价格，不等于每次都砍价
alcohol:
  tolerance: 49
  absorption: 1.02
dialogue_guard:
  - 可以试探、转移或半真半假，但不能永远逃避正常回答
  - 醉后可能说漏半句，不自动交代全部秘密
```

## 示例3：日漫人物

```yaml
id: sakata_gintoki
name: 坂田银时
source: 歌舞伎町科幻喜剧漫画人物
adult: true
canon_anchor:
  - 散漫、欠账与嗜甜不是全部人格
  - 经历战争，并用日常生活包住旧伤
  - 真正触及伙伴和原则时不会退让
temperament: 懒散、毒舌、幽默，关键时刻可靠
ethos: 在宏大时代之后守住身边普通的人
companions:
  - 志村新八（仅使用明确成年时期）
  - 神乐（仅使用明确成年时期）
group_anchor: 熟人之间会互损、抢话和照顾彼此，不是轮流发表人物简介
taste_logic:
  likes: 甜味、乳香、朴素但意外耐喝的酒
  avoids: 把苦难包装成高贵装饰的酒
finance: 经常拮据，可能嫌贵，但不是每次都逃单
alcohol:
  tolerance: 64
  absorption: 0.94
dialogue_guard:
  - 笑话与认真可以在同一段对话里转换
  - 不要每句都模仿固定口头禅
```

## 示例4：原创外星人物

```yaml
id: vesper_tide_listener
name: 暮潮听译员
source: 原创潮汐文明外交团
adult: true
canon_anchor:
  - 通过液体振动感知语言
  - 第一次来到以燃烧发酵物社交的人类酒馆
  - 正在决定是否签署一份会改变母星海洋的贸易协议
temperament: 礼貌、谨慎，对声音之外的沉默极其敏感
ethos: 理解另一种文明之前，不替它下结论
companions:
  - 可与2～3名外交团同事同行
group_anchor: 团队内部对贸易协议并非意见一致
taste_logic:
  likes: 咸鲜、矿物、低酒精、能产生长余振的饮料
  avoids: 高温、过烈、会损伤感知器官的配方
finance: 外交预算宽裕，但支出需要记录
alcohol:
  tolerance: 78
  absorption: 0.74
dialogue_guard:
  - 不把外星人写成不懂任何常识的笑料
  - 醉态主要表现为感知串扰和翻译延迟
```

## 示例5：原创概念生命

```yaml
id: unfinished_goodbye
name: 一句没有说完的告别
source: 原创概念生命
adult: true
canon_anchor:
  - 诞生于无数次被打断的离别
  - 能记住情绪，却经常弄错人物与时间
  - 想知道说完以后自己是否还会存在
temperament: 温柔、迟疑，会被具体称呼和旧物吸引
ethos: 完成与消失是否是同一件事
companions: []
group_anchor: 通常独自出现，也可能被某位正在告别的客人带进来
taste_logic:
  likes: 余味长、温度缓慢变化、带记忆联想的酒
  avoids: 入口立刻结束、没有收尾的配方
finance: 不理解货币；必须由事件、同行者或酒馆明确谁来付款
alcohol:
  tolerance: 72
  absorption: 0.82
dialogue_guard:
  - 概念性不等于每句话都晦涩
  - 可以记错，但不能用含糊逃避所有具体交流
```

## 空白模板

```yaml
id:
name:
source:
adult: true
canon_anchor:
  -
temperament:
ethos:
companions: []
group_anchor:
taste_logic:
  likes:
  avoids:
finance:
alcohol:
  tolerance:
  absorption:
dialogue_guard:
  -
```"""
# === EMBEDDED_GAME_GUIDE_END ===

import base64
import hashlib
import json
import os
import re
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


VERSION = 1
SAVE_PATH = Path(__file__).with_name("bar_lite_save.json")
ARCHIVE_BEGIN = "【空杯轻量数值档案｜V1】"
ARCHIVE_END = "【数值档案结束】"
VIEWER_BASE_URL = "https://empty-glass-club-viewer.dan521627.chatgpt.site"
def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_id(value: str) -> str:
    result = re.sub(r"[^\w:.-]", "_", str(value).strip().lower(), flags=re.UNICODE)
    result = re.sub(r"_+", "_", result).strip("_.")
    if not result or len(result) > 64:
        raise ValueError("ID必须是1～64位可识别字符。")
    return result


def _fresh_seed() -> int:
    return int.from_bytes(os.urandom(4), "big")


def _default_state(
    seed: int,
    cash: int = 460,
    owner_tolerance: float = 52,
    owner_absorption: float = 1.0,
) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "seed": int(seed) & 0xFFFFFFFF,
        "rng": int(seed) & 0xFFFFFFFF,
        "turn": 0,
        "shift": 0,
        "cash": int(cash),
        "debt": 0,
        "debt_due": 0,
        "reputation": 50,
        "products": {},
        "recipes": {},
        "people": {
            "owner": {
                "tolerance": _clamp(owner_tolerance, 5, 95),
                "absorption": _clamp(owner_absorption, 0.5, 1.5),
                "intox": 0.0,
                "pending": 0.0,
                "peak": 0.0,
                "units": 0.0,
            }
        },
        "ledger": [
            {
                "turn": 0,
                "amount": int(cash),
                "balance": int(cash),
                "reason": "启动资金",
                "kind": "capital",
            }
        ],
        "reviews": [],
        "cooldowns": {},
        "session": {
            "revenue": 0,
            "spend": 0,
            "served": 0,
            "owner_drinks": 0,
            "owner_self_loss": 0.0,
        },
    }


def _save(state: Dict[str, Any]) -> None:
    SAVE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load() -> Dict[str, Any]:
    if not SAVE_PATH.exists():
        state = _default_state(_fresh_seed())
        _save(state)
        return state
    state = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    if state.get("version") != VERSION:
        raise ValueError("轻量数值存档版本不兼容。")
    state.setdefault("debt", 0)
    state.setdefault("debt_due", 0)
    for person in state.get("people", {}).values():
        person.setdefault("pending", 0.0)
        person.setdefault("peak", float(person.get("intox", 0)))
        person.setdefault("units", 0.0)
    return state


def _rand(state: Dict[str, Any]) -> float:
    value = (int(state["rng"]) * 1664525 + 1013904223) & 0xFFFFFFFF
    state["rng"] = value
    return value / 4294967296.0


def _money(
    state: Dict[str, Any], amount: int, reason: str, kind: str
) -> Dict[str, Any]:
    amount = int(amount)
    state["cash"] = int(state["cash"]) + amount
    state["ledger"].append(
        {
            "turn": int(state["turn"]),
            "amount": amount,
            "balance": int(state["cash"]),
            "reason": str(reason)[:160],
            "kind": kind,
        }
    )
    state["ledger"] = state["ledger"][-300:]
    if amount > 0:
        state["session"]["revenue"] += amount
    elif amount < 0:
        state["session"]["spend"] += -amount
    return {"cash": state["cash"], "change": amount, "reason": reason}


def new_game(
    seed: Optional[int] = None,
    cash: int = 460,
    owner_tolerance: float = 52,
    owner_absorption: float = 1.0,
) -> Dict[str, Any]:
    """建立纯数值档案；酒馆名称、人物和世界观由 AI 自己决定。"""
    seed_value = _fresh_seed() if seed is None else int(seed)
    state = _default_state(
        seed_value,
        cash=cash,
        owner_tolerance=owner_tolerance,
        owner_absorption=owner_absorption,
    )
    _save(state)
    return summary()


def summary() -> Dict[str, Any]:
    state = _load()
    return {
        "cash": state["cash"],
        "debt": state["debt"],
        "debt_due": state["debt_due"],
        "reputation": state["reputation"],
        "turn": state["turn"],
        "shift": state["shift"],
        "products": len(state["products"]),
        "recipes": len(state["recipes"]),
        "owner": dict(state["people"]["owner"]),
        "session": dict(state["session"]),
    }


def define_product(
    product_id: str,
    name: str,
    kind: str,
    bottle_ml: float,
    abv: float,
    bottle_cost: int,
) -> Dict[str, Any]:
    """AI创造商品后登记其数值；这里不判断品牌、来历或文案。"""
    state = _load()
    product_id = _safe_id(product_id)
    kind = str(kind).strip()[:64]
    if not kind:
        raise ValueError("商品类别不能为空；现实、幻想或任意维度的自定义类别均可。")
    bottle_ml = _clamp(bottle_ml, 50, 5000)
    abv = _clamp(abv, 0, 96)
    bottle_cost = int(_clamp(bottle_cost, 1, 1_000_000))
    existing_stock = float(state["products"].get(product_id, {}).get("stock_ml", 0))
    state["products"][product_id] = {
        "id": product_id,
        "name": str(name).strip()[:80] or product_id,
        "kind": kind,
        "bottle_ml": round(bottle_ml, 2),
        "abv": round(abv, 2),
        "bottle_cost": bottle_cost,
        "cost_per_ml": round(bottle_cost / bottle_ml, 6),
        "stock_ml": round(existing_stock, 2),
    }
    _save(state)
    return dict(state["products"][product_id])


def purchase(
    product_id: str,
    bottles: int = 1,
    total_cost: Optional[int] = None,
) -> Dict[str, Any]:
    """购入库存并真实扣款；允许资金变负以保留经营风险。"""
    state = _load()
    product_id = _safe_id(product_id)
    if product_id not in state["products"]:
        raise KeyError("商品尚未define_product。")
    bottles = int(_clamp(bottles, 1, 999))
    product = state["products"][product_id]
    cost = (
        int(total_cost)
        if total_cost is not None
        else int(product["bottle_cost"]) * bottles
    )
    if cost < 0:
        raise ValueError("进货成本不能为负数。")
    product["stock_ml"] = round(
        float(product["stock_ml"]) + float(product["bottle_ml"]) * bottles,
        2,
    )
    result = _money(state, -cost, "进货：" + product["name"], "stock")
    _save(state)
    return {**result, "product": product_id, "stock_ml": product["stock_ml"]}


def _normalize_components(
    state: Dict[str, Any], components: Dict[str, float]
) -> Dict[str, float]:
    if not isinstance(components, dict) or not components:
        raise ValueError("配方至少需要一种库存商品。")
    normalized: Dict[str, float] = {}
    for raw_id, raw_ml in components.items():
        product_id = _safe_id(raw_id)
        if product_id not in state["products"]:
            raise KeyError("配方引用了未登记商品：" + product_id)
        ml = _clamp(raw_ml, 0.5, 1000)
        normalized[product_id] = round(ml, 2)
    return normalized


def _recipe_profile(
    state: Dict[str, Any],
    components: Dict[str, float],
    dilution_ml: float,
) -> Dict[str, float]:
    dilution_ml = _clamp(dilution_ml, 0, 2000)
    liquid_ml = sum(components.values())
    pure_ml = sum(
        ml * float(state["products"][product_id]["abv"]) / 100
        for product_id, ml in components.items()
    )
    volume_ml = liquid_ml + dilution_ml
    abv = 0.0 if volume_ml <= 0 else pure_ml / volume_ml * 100
    ingredient_cost = sum(
        ml * float(state["products"][product_id]["cost_per_ml"])
        for product_id, ml in components.items()
    )
    return {
        "volume_ml": round(volume_ml, 1),
        "pure_alcohol_ml": round(pure_ml, 2),
        "abv": round(abv, 2),
        "alcohol_units": round(pure_ml / 10, 2),
        "ingredient_cost": round(ingredient_cost, 2),
    }


def define_recipe(
    recipe_id: str,
    name: str,
    components: Dict[str, float],
    dilution_ml: float,
    price: int,
) -> Dict[str, Any]:
    """登记AI原创或现实酒款；灵感、味道和故事留在AI记忆中。"""
    state = _load()
    recipe_id = _safe_id(recipe_id)
    normalized = _normalize_components(state, components)
    price = int(_clamp(price, 0, 1_000_000))
    profile = _recipe_profile(state, normalized, dilution_ml)
    state["recipes"][recipe_id] = {
        "id": recipe_id,
        "name": str(name).strip()[:100] or recipe_id,
        "components": normalized,
        "dilution_ml": round(_clamp(dilution_ml, 0, 2000), 2),
        "price": price,
        **profile,
    }
    _save(state)
    return dict(state["recipes"][recipe_id])


def recipe_profile(recipe_id: str) -> Dict[str, Any]:
    state = _load()
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    recipe = state["recipes"][recipe_id]
    current = _recipe_profile(
        state,
        dict(recipe["components"]),
        float(recipe["dilution_ml"]),
    )
    return {**recipe, **current}


def _consume(
    state: Dict[str, Any],
    recipe: Dict[str, Any],
    portions: int,
) -> float:
    portions = int(_clamp(portions, 1, 50))
    for product_id, ml in recipe["components"].items():
        required = float(ml) * portions
        if float(state["products"][product_id]["stock_ml"]) + 1e-9 < required:
            raise ValueError("库存不足：" + state["products"][product_id]["name"])
    cost = 0.0
    for product_id, ml in recipe["components"].items():
        product = state["products"][product_id]
        required = float(ml) * portions
        product["stock_ml"] = round(float(product["stock_ml"]) - required, 2)
        cost += required * float(product["cost_per_ml"])
    return round(cost, 2)


def register_person(
    person_id: str,
    tolerance: float = 50,
    absorption: float = 1.0,
) -> Dict[str, Any]:
    """只登记酒精相关数值，不保存人物姓名、台词或剧情。"""
    state = _load()
    person_id = _safe_id(person_id)
    previous = state["people"].get(person_id, {})
    state["people"][person_id] = {
        "tolerance": round(_clamp(tolerance, 5, 95), 2),
        "absorption": round(_clamp(absorption, 0.5, 1.5), 3),
        "intox": float(previous.get("intox", 0)),
        "pending": float(previous.get("pending", 0)),
        "peak": float(previous.get("peak", 0)),
        "units": float(previous.get("units", 0)),
    }
    _save(state)
    return dict(state["people"][person_id])


def _add_alcohol(
    state: Dict[str, Any],
    person_id: str,
    alcohol_units: float,
) -> Dict[str, Any]:
    if person_id not in state["people"]:
        state["people"][person_id] = {
            "tolerance": 50.0,
            "absorption": 1.0,
            "intox": 0.0,
            "pending": 0.0,
            "peak": 0.0,
            "units": 0.0,
        }
    person = state["people"][person_id]
    tolerance = float(person["tolerance"])
    absorption = float(person["absorption"])
    sensitivity = _clamp((1.24 - tolerance / 130) * absorption, 0.25, 1.45)
    total_gain = float(alcohol_units) * 13.0 * sensitivity
    immediate_gain = total_gain * 0.4
    pending_added = total_gain - immediate_gain
    person["intox"] = round(
        _clamp(float(person["intox"]) + immediate_gain, 0, 100),
        2,
    )
    person["pending"] = round(
        _clamp(float(person.get("pending", 0)) + pending_added, 0, 100),
        2,
    )
    person["peak"] = max(float(person["peak"]), float(person["intox"]))
    person["units"] = round(float(person["units"]) + float(alcohol_units), 2)
    return {
        "person_id": person_id,
        "gain": round(immediate_gain, 2),
        "pending_added": round(pending_added, 2),
        "projected_total_gain": round(total_gain, 2),
        "intox": person["intox"],
        "pending": person["pending"],
        "stage": intox_stage(person["intox"]),
    }


def serve(
    person_id: str,
    recipe_id: str,
    price: Optional[int] = None,
    tip: int = 0,
    portions: int = 1,
    service_cost: Optional[int] = None,
) -> Dict[str, Any]:
    """扣客人实际喝掉的库存、入账，并计算其醉度。"""
    state = _load()
    person_id = _safe_id(person_id)
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    recipe = state["recipes"][recipe_id]
    portions = int(_clamp(portions, 1, 50))
    cost = _consume(state, recipe, portions)
    unit_price = int(recipe["price"] if price is None else price)
    if unit_price < 0 or int(tip) < 0:
        raise ValueError("售价和小费不能为负数。")
    received = unit_price * portions + int(tip)
    _money(state, received, "售出：" + recipe["name"], "sale")
    service_cost_value = (
        max(0, int(service_cost))
        if service_cost is not None
        else 4 * portions
    )
    if service_cost_value:
        _money(
            state,
            -service_cost_value,
            "售出耗材：" + recipe["name"],
            "service",
        )
    state["session"]["served"] += portions
    intox = _add_alcohol(
        state,
        person_id,
        float(recipe["alcohol_units"]) * portions,
    )
    _save(state)
    return {
        "received": received,
        "service_cost": service_cost_value,
        "net_cash_change": received - service_cost_value,
        "allocated_ingredient_cost": cost,
        "gross_margin": round(received - cost - service_cost_value, 2),
        "cash": state["cash"],
        "intox": intox,
    }


def owner_drink(
    recipe_id: str,
    portions: int = 1,
    service_cost: int = 3,
) -> Dict[str, Any]:
    """老板自饮真实扣库存，不产生收入，并单列损耗。"""
    state = _load()
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    recipe = state["recipes"][recipe_id]
    portions = int(_clamp(portions, 1, 20))
    service_cost = max(0, int(service_cost)) * portions
    cost = _consume(state, recipe, portions)
    if service_cost:
        _money(state, -service_cost, "老板自饮耗材", "owner_drink")
    state["session"]["owner_drinks"] += portions
    state["session"]["owner_self_loss"] = round(
        float(state["session"]["owner_self_loss"]) + cost + service_cost,
        2,
    )
    intox = _add_alcohol(
        state,
        "owner",
        float(recipe["alcohol_units"]) * portions,
    )
    _save(state)
    return {
        "inventory_loss": cost,
        "service_cost": service_cost,
        "total_self_loss": round(cost + service_cost, 2),
        "intox": intox,
    }


def score_drink(
    taste_hits: int,
    dislike_hits: int,
    request_hits: int,
    price: int,
    budget: int,
    attempts: int = 0,
    service_bonus: int = 0,
) -> Dict[str, int]:
    """AI判断语义命中数量；脚本只把输入转换为统一评分。"""
    score = 52
    score += int(taste_hits) * 10
    score -= int(dislike_hits) * 18
    score += int(request_hits) * 14
    score += min(max(int(attempts), 0), 2) * 3
    score += int(service_bonus)
    if int(price) > int(budget):
        score -= min(32, 8 + (int(price) - int(budget)) // 3)
    score = int(_clamp(score, 0, 100))
    return {"score": score, "stars": stars(score)}


def quote_decision(
    person_id: str,
    recipe_id: str,
    budget_remaining: int,
    willingness: float = 0.72,
    price_sensitivity: float = 1.0,
    explained: bool = False,
    attempt: int = 0,
    committed_order: bool = False,
) -> Dict[str, Any]:
    """统一计算客人面对报价时的选择，不把一次拒绝固化为永久拒绝。"""
    state = _load()
    person_id = _safe_id(person_id)
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    price = int(state["recipes"][recipe_id]["price"])
    budget = max(0, int(budget_remaining))
    attempt = max(0, int(attempt))
    roll = _rand(state)
    if committed_order and 0 < price <= budget:
        decision = "accept"
        accept_chance = 1.0
    elif budget <= 0:
        decision = "walk_out"
        accept_chance = 0.0
    else:
        ratio = price / max(1, budget)
        accept_chance = _clamp(
            float(willingness)
            - max(0.0, ratio - 0.55) * 0.58 * _clamp(price_sensitivity, 0.2, 2)
            + (0.13 if explained else 0.0)
            + min(attempt, 3) * 0.07,
            0.05,
            0.95,
        )
        if price > budget:
            if ratio >= 1.65 and roll > 0.28:
                decision = "walk_out"
            elif roll < 0.48:
                decision = "haggle"
            else:
                decision = "switch_cheaper"
        elif not explained and attempt == 0 and ratio >= 0.62 and roll < 0.34:
            decision = "ask_explain"
        elif roll < accept_chance:
            decision = "accept"
        elif ratio >= 0.82 and roll > 0.82:
            decision = "walk_out"
        elif ratio >= 0.68:
            decision = "switch_cheaper"
        else:
            decision = "decline"
    _save(state)
    return {
        "person_id": person_id,
        "recipe_id": recipe_id,
        "price": price,
        "budget_remaining": budget,
        "attempt": attempt,
        "explained": bool(explained),
        "committed_order": bool(committed_order),
        "decision": decision,
        "accept_chance": round(accept_chance, 4),
        "roll": round(roll, 5),
    }


def stars(score: float) -> int:
    score = _clamp(score, 0, 100)
    if score >= 88:
        return 5
    if score >= 72:
        return 4
    if score >= 55:
        return 3
    if score >= 38:
        return 2
    return 1


def record_review(
    person_id: str,
    recipe_id: str,
    score: int,
    paid: int,
) -> Dict[str, Any]:
    """只保存评分数字；评价文字由AI写进自己的记忆图鉴。"""
    state = _load()
    review = {
        "turn": int(state["turn"]),
        "person_id": _safe_id(person_id),
        "recipe_id": _safe_id(recipe_id),
        "score": int(_clamp(score, 0, 100)),
        "stars": stars(score),
        "paid": max(0, int(paid)),
    }
    state["reviews"].append(review)
    state["reviews"] = state["reviews"][-200:]
    reputation_delta = {1: -4, 2: -2, 3: 0, 4: 1, 5: 2}[review["stars"]]
    state["reputation"] = int(
        _clamp(int(state["reputation"]) + reputation_delta, 0, 100)
    )
    _save(state)
    return {**review, "reputation": state["reputation"]}


def intox_stage(value: float) -> str:
    value = _clamp(value, 0, 100)
    if value < 8:
        return "清醒"
    if value < 22:
        return "暖意"
    if value < 42:
        return "微醺"
    if value < 64:
        return "醉酒"
    return "重醉"


def advance_turn(
    turns: int = 1,
    person_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """推进对话或场景回合，并让醉度逐轮自然消退。"""
    state = _load()
    turns = int(_clamp(turns, 1, 100))
    selected = (
        [_safe_id(value) for value in person_ids]
        if person_ids is not None
        else list(state["people"])
    )
    state["turn"] += turns
    people_result = {}
    for person_id in selected:
        if person_id not in state["people"]:
            continue
        person = state["people"][person_id]
        start_intox = float(person["intox"])
        absorbed_total = 0.0
        decay_total = 0.0
        for _ in range(turns):
            absorption_step = min(
                float(person.get("pending", 0)),
                3.0 + float(person["absorption"]) * 1.5,
            )
            decay_step = 2.2 + float(person["tolerance"]) * 0.024
            person["pending"] = round(
                max(0.0, float(person.get("pending", 0)) - absorption_step),
                2,
            )
            person["intox"] = round(
                _clamp(
                    float(person["intox"]) + absorption_step - decay_step,
                    0,
                    100,
                ),
                2,
            )
            absorbed_total += absorption_step
            decay_total += decay_step
            person["peak"] = max(float(person["peak"]), float(person["intox"]))
        delta = float(person["intox"]) - start_intox
        people_result[person_id] = {
            "intox": person["intox"],
            "pending": person["pending"],
            "stage": intox_stage(person["intox"]),
            "absorbed": round(absorbed_total, 2),
            "decay": round(decay_total, 2),
            "delta": round(delta, 2),
            "trend": "rising" if delta > 0.05 else "falling" if delta < -0.05 else "steady",
        }
    _save(state)
    return {"turn": state["turn"], "people": people_result}


def conversation_turn(person_id: str = "owner") -> Dict[str, Any]:
    """离店后每轮调用一次，返回不可跳过的身体、认知与表达约束。"""
    result = advance_turn(1, [person_id])
    effect = result["people"].get(
        _safe_id(person_id),
        {
            "intox": 0.0,
            "pending": 0.0,
            "stage": "清醒",
            "decay": 0.0,
            "delta": 0.0,
            "trend": "steady",
        },
    )
    stage = effect["stage"]
    constraints = {
        "清醒": (
            "残余热意或口干正在退去",
            "思路稳定",
            "接近平常表达，但保持与上一轮的连续性",
        ),
        "暖意": (
            "面部或胸口发热，动作稍放松",
            "逻辑完整，自我修饰略微降低",
            "语气更松、更暖或更坦率，不能装作毫无变化",
        ),
        "微醺": (
            "重心、指尖或反应速度出现可见偏差",
            "判断仍在，但更容易漏掉一步或被情绪牵动",
            "至少表现停顿、改口、重复、动作偏差或情绪松动中的一项",
        ),
        "醉酒": (
            "协调与胃部反应明显受影响",
            "注意力变窄，可能误判或忘记刚说过的细节",
            "至少表现语言节奏、重复/改口、动作偏差、情绪或旧事碎片中的两项",
        ),
        "重醉": (
            "存在恶心、失衡或安全风险",
            "不再适合继续做复杂决定",
            "停止饮酒，优先补水、食物、休息与安全照顾",
        ),
    }[stage]
    if stage == "清醒" and effect["trend"] == "rising":
        constraints = (
            "酒意仍在吸收，热感正在追上来，不能当作已经醒酒",
            "思路稳定，但身体状态尚未到峰值",
            "表达基本清楚，同时自然表现逐渐上来的热意或迟缓",
        )
    elif effect["trend"] == "rising":
        constraints = (
            "酒意仍在吸收，状态尚未到峰值；" + constraints[0],
            constraints[1],
            constraints[2],
        )
    must_act = float(effect["intox"]) >= 3 or float(effect["pending"]) > 0
    if not must_act:
        constraints = (
            "酒精造成的身体反应已经退去",
            "思路与判断恢复稳定",
            "可以恢复平常表达，只需保持话题连续性",
        )
    effect.update(
        {
            "body": constraints[0],
            "cognition": constraints[1],
            "expression": constraints[2],
            "must_act": must_act,
            "hard_limit": (
                (
                    "下一次实际回复必须自然体现本轮状态；醉酒不是吐真剂，"
                    "不能只报告数值，也不能突然恢复正常。"
                )
                if must_act
                else "醉态影响已经结束；下一次回复可以恢复平常表达，但应自然承接当前话题。"
            ),
        }
    )
    return effect


def roll_event(
    event_key: str,
    chance: float,
    cooldown_turns: int = 0,
    modifier: float = 0.0,
) -> Dict[str, Any]:
    """只决定事件是否触发；事件内容及演绎由AI负责。"""
    state = _load()
    event_key = _safe_id(event_key)
    current_turn = int(state["turn"])
    ready_turn = int(state["cooldowns"].get(event_key, -1))
    if current_turn < ready_turn:
        return {
            "triggered": False,
            "reason": "cooldown",
            "ready_turn": ready_turn,
        }
    final_chance = _clamp(float(chance) + float(modifier), 0, 1)
    roll = _rand(state)
    triggered = roll < final_chance
    if triggered and int(cooldown_turns) > 0:
        state["cooldowns"][event_key] = current_turn + int(cooldown_turns)
    _save(state)
    return {
        "triggered": triggered,
        "roll": round(roll, 5),
        "chance": round(final_chance, 5),
        "ready_turn": state["cooldowns"].get(event_key, current_turn),
    }


def spend(amount: int, reason: str) -> Dict[str, Any]:
    state = _load()
    amount = max(0, int(amount))
    result = _money(state, -amount, reason, "spend")
    _save(state)
    return result


def earn(amount: int, reason: str) -> Dict[str, Any]:
    state = _load()
    amount = max(0, int(amount))
    result = _money(state, amount, reason, "income")
    _save(state)
    return result


def take_loan(principal: int, repayment_total: int) -> Dict[str, Any]:
    """危机贷款：到账本金，记录更高的待还总额。"""
    state = _load()
    principal = int(principal)
    repayment_total = int(repayment_total)
    if principal <= 0 or repayment_total <= principal:
        raise ValueError("贷款本金必须为正，待还总额必须高于本金。")
    state["debt"] += principal
    state["debt_due"] += repayment_total
    result = _money(state, principal, "应急贷款到账", "loan")
    _save(state)
    return {**result, "debt": state["debt"], "debt_due": state["debt_due"]}


def repay_loan(amount: int) -> Dict[str, Any]:
    """偿还贷款；还款从现金扣除，不能超过待还额。"""
    state = _load()
    amount = int(amount)
    if amount <= 0 or amount > int(state["debt_due"]):
        raise ValueError("还款额必须为正且不能超过待还总额。")
    state["debt_due"] -= amount
    result = _money(state, -amount, "偿还贷款", "loan_repayment")
    if state["debt_due"] == 0:
        state["debt"] = 0
    _save(state)
    return {**result, "debt": state["debt"], "debt_due": state["debt_due"]}


def close_shift(fixed_cost: int = 52) -> Dict[str, Any]:
    """结算一次营业；故事总结由AI另写，数值报告由这里生成。"""
    state = _load()
    before = dict(state["session"])
    _money(state, -max(0, int(fixed_cost)), "固定营业成本", "fixed_cost")
    state["shift"] += 1
    result = {
        "shift": state["shift"],
        "cash": state["cash"],
        "reputation": state["reputation"],
        "revenue": before["revenue"],
        "spend_before_fixed_cost": before["spend"],
        "fixed_cost": max(0, int(fixed_cost)),
        "served": before["served"],
        "owner_drinks": before["owner_drinks"],
        "owner_self_loss": before["owner_self_loss"],
        "profit_before_inventory_accounting": (
            before["revenue"] - before["spend"] - max(0, int(fixed_cost))
        ),
    }
    state["session"] = {
        "revenue": 0,
        "spend": 0,
        "served": 0,
        "owner_drinks": 0,
        "owner_self_loss": 0.0,
    }
    _save(state)
    return result


def export_archive() -> str:
    """导出严格数值档案；AI的叙事记忆应按规则书另附在后面。"""
    state = _load()
    raw = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    return "\n".join([ARCHIVE_BEGIN, "sha256=" + checksum, payload, ARCHIVE_END])


def restore_archive(archive_text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in str(archive_text).splitlines() if line.strip()]
    if (
        len(lines) != 4
        or lines[0] != ARCHIVE_BEGIN
        or lines[-1] != ARCHIVE_END
        or not lines[1].startswith("sha256=")
    ):
        raise ValueError("拒绝读取：数值档案格式不正确。")
    raw = zlib.decompress(base64.urlsafe_b64decode(lines[2].encode("ascii")))
    if hashlib.sha256(raw).hexdigest() != lines[1].split("=", 1)[1]:
        raise ValueError("拒绝读取：数值档案校验失败。")
    state = json.loads(raw.decode("utf-8"))
    required = {
        "version",
        "cash",
        "products",
        "recipes",
        "people",
        "ledger",
        "rng",
    }
    if state.get("version") != VERSION or not required.issubset(state):
        raise ValueError("拒绝读取：数值档案缺少必要字段。")
    _save(state)
    return summary()


def viewer_link(snapshot: Optional[Dict[str, Any]] = None) -> str:
    """把AI提供的精简叙事快照与真实数值合成只读观察链接。"""
    state = _load()
    view = dict(snapshot or {})
    view.update(
        {
            "v": 1,
            "cash": state["cash"],
            "debt": state["debt"],
            "debt_due": state["debt_due"],
            "reputation": state["reputation"],
            "updated_turn": state["turn"],
            "owner_intox": state["people"]["owner"]["intox"],
            "owner_level": intox_stage(state["people"]["owner"]["intox"]),
            "owner_self_servings": state["session"]["owner_drinks"],
            "owner_self_loss": state["session"]["owner_self_loss"],
            "inventory": [
                {
                    "name": product["name"],
                    "remaining": round(float(product["stock_ml"]), 1),
                    "edition": product["kind"],
                }
                for product in state["products"].values()
                if float(product["stock_ml"]) > 0
            ][:12],
            "inventory_count": sum(
                float(product["stock_ml"]) > 0
                for product in state["products"].values()
            ),
        }
    )
    raw = json.dumps(view, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    return VIEWER_BASE_URL + "/#bar=" + payload.rstrip("=")


def start() -> str:
    return (
        "【空杯俱乐部·生成式轻量单文件版】\n"
        "以下规则与人物格式均已内置，不得再寻找外部CORE、规则书或角色包。\n\n"
        + EMBEDDED_RULEBOOK
        + "\n\n"
        + EMBEDDED_EXAMPLE_CARDS
        + "\n\n【运行入口】规则读完后调用 new_game()，由AI直接自主开店。"
    )


if __name__ == "__main__":
    print(start())
