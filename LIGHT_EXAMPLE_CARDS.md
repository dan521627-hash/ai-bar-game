# 生成式轻量版：人物卡示例

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
```
