#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2025/4
@Author  : cursor
@Prompt  : gemini2.5, claude
@File    : author_actions.py
"""

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field
from metagpt.utils.author_storage import NovelBackground
from metagpt.actions.action import Action
from metagpt.logs import logger
from metagpt.schema import BaseContext, Message

class Status(Enum):
    FIRST = "first"
    FIX = "fix"
    FINISHED = 'finished'

SYNOPSIS_FIRST_TEMPLATE = """
# 任务
以专业作家的严谨态度，构建一部小说的总纲。

## 输入分析
从**用户输入**中提取以下信息：
1. 小说题材
2. 小说总长度
3. 部分原始总纲
若以上信息存在，则严格遵守用户输入，补全剩余信息，构建小说总纲。
若以上信息中存在缺失，则根据用户输入自行推理，构建完整小说总纲。


## 创作要求
1. 核心剧情框架
- 构建完整的世界观，包括年代、地点、社会规则等
- 设计阶梯式的冲突和驱动力，驱动故事发展
- 以大章节为单位规划剧情，设计每个大章节的关键剧情
- 为每个大章节预留多个悬念"种子"；为悬念设计多种迷惑性的解读方式
- 设计多线剧情发展，并安排合理的多线剧情交叉
- 设置多种剧情伏笔，保证伏笔闭环
- 规划信息的释放节奏，明确早期揭示的信息和后期保留的信息

2. 核心人物塑造
- 设定主要角色的性格、内在驱动力，矛盾和预期发展轨迹，规划角色的人物弧光
- 设计角色的剧情定位，技能，组织阵营
- 规划角色之间的人物关系及后续变化

3. 主题构思与融入
- 确定3-5个故事主题关键词，如（爱、牺牲、自由、亲情、宿命、成长等）
- 规划主题的呈现方式，包括通过主角成长/抉择、情节象征意义或特定人物关系展现
- 确保关键情节和人物弧光服务于或挑战选定的主题
- 设计语言气质和写作风格

4. 反思
- 进行逻辑一致性检查，识别并修正潜在的逻辑漏洞、时间线问题或设定矛盾

## 输出要求
1. 不能为剧情、人物、伏笔等设定明确的章节
2. 输出纯文本格式，不能包含图，代码，表格等
3. 不能输出总纲以外内容，如反问和建议
"""

SYNOPSIS_CONDITION_TEMPLATE = """
# 总纲约束

## 任务说明
后续内容独立创作,但需检查不违背总纲设定。

## 总纲
{synopsis}

## 约束条件
1. 世界观一致性
- 时间线：不能违背总纲中的时间设定
- 地理环境：保持与总纲中地理描述的一致性
- 社会规则：遵循总纲中的社会体系设定

2. 人物关系一致性
- 核心人物：保持与总纲中人物设定的统一
- 人物关系：不能违背总纲中的人物关系网
- 人物发展：符合总纲中的人物成长轨迹

3. 剧情发展一致性
- 主线剧情：不能偏离总纲中的核心剧情框架
- 关键事件：保持与总纲中关键事件的关联
- 伏笔设置：不能破坏总纲中的伏笔设计

4. 主题一致性
- 核心主题：保持与总纲主题的统一
- 价值取向：不能违背总纲中的价值体系
- 情感基调：符合总纲中的情感表达
"""

###########################################

CHARACTER_FIRST_TEMPLATE = """
# 小说角色设计规范

## 任务说明
根据**用户输入**的背景信息，设计一个小说角色。
如果是主要角色，需包含立体的人物塑造、清晰的叙事定位和合理的人物发展。配角可以略作简化。

## 设计维度
1. 核心属性
- 姓名：符合世界观的全名
- 别名：别名/绰号
- 生理特征：年龄/性别
- 外貌: 详细阐述外貌特点，外貌设定要符合角色性格
- 时代背景：角色所处的历史时期或特殊时间节点

2. 人格塑造
- 性格矩阵：
  - 核心特质（3-5个关键词）
  - 外在表现 vs 内在本质
  - 道德坐标
- 行为模式：
  - 肢体语言/习惯用语
  - 决策倾向（理性/感性比例）

3. 叙事定位
- 角色原型：脸谱化的角色定位类别（如英雄/导师/挚友/反派/魔王/隐士/殉道者等）
- 关系图谱（纯文本形式）：
  - 与其他核心角色的情感连结强度
  - 关键矛盾对象
- 功能价值：推动情节的核心事件触发器

4. 发展轨迹
- 角色弧光：
  - 初始状态 → 转折点1 → 转折点2 → ... → 转折点n → 终极状态
  - 能力成长树（可量化的技能变化）
- 象征意义：代表的核心主题或隐喻

## 输出格式
JSON格式输出
{{
    "name": "人物标准全名"
    "other": "除全名外其他信息"
    ""
}}
"""

###########################################

OUTLINE_FIRST_TEMPLATE = """
# 章节大纲创作规范

## 任务说明
严格遵循**用户输入**中的要求，创作新章节的大纲。

## 创作要点
1. 核心剧情
   - 设计1-2个关键情节节点
   - 明确本章对前后文的作用（如：承接前文、埋下伏笔、推进主线等）

2. 细节描写
   - 选择1-2个重要场景进行详细描写
   - 通过细节展现人物性格或推动情节发展
   - 在适当位置设置悬念或伏笔

3. 人物刻画
   - 展现主要角色的行为特征
   - 通过对话或动作体现人物关系变化

## 输出要求
1. 大纲需包含：章节标题、核心剧情、重要场景、关键细节
2. 内容按时间顺序，以剧情流的形式简明叙述
3. 章节对应字数5000字内，注意控制章节大纲剧情密度
3. 确保剧情不与**总纲约束**矛盾，与**前文章节大纲**自然衔接
4. 不能提及之后章节的剧情
"""

###########################################

OUTLINE_CONDITION_TEMPLATE = """
# 前序章节大纲
{previous_outlines}

## 创作要求
新章节需与前文保持连贯，注意：

1. 剧情衔接
- 不产生矛盾
- 承接伏笔
- 紧扣主线

2. 人物一致
- 延续性格发展
- 自然融入新角色

3. 情感连贯
- 延续感情线
- 合理情感变化

4. 细节呼应
- 重要场景道具一致
- 时间线合理

确保新内容与前文统一。
"""

###########################################

BACKGROUND_CONDITION_TEMPLATE = """
# 背景设定
{background_settings}

## 创作限制
后续创作需要遵循已有的背景设定:

1. 人物的性格、能力、经历不能改变，人物关系要符合设定
2. 地点的地理位置和环境特征不变，场景描写符合设定
3. 组织结构和规则不变，成员行为符合组织特性
4. 物品属性和作用不变

请确保新创作的内容不会与已有背景设定产生冲突。
"""

###########################################

CHAPTERS_FIRST_TEMPLATE = """
# 任务: 根据**本章大纲**进行扩写

## 扩写要求
1. 严格遵信**用户输入**要求，如字数和写作风格
2. 遵循**本章大纲**中的剧情发展
3. 实体设定不与**背景设定**冲突
4. 扩写后检查前后段落的连贯性
5. 默认写作风格:
   - 描写细致,注意补充细节,如景物外观、人物外貌、环境氛围
   - 善用比喻、通感、拟人等修辞手法
   - 人物对话自然流畅，注意捕捉人物内心活动，语言风格符合人物设定
6. 扩写总字数满足要求，默认为2000-4000字

## 输出格式
1.输出纯文本，不能包含图，代码，表格等
2.不输出章节以外内容，如反问和建议
"""

###########################################

FIX_TEMPLATE = """
# 任务
#范本是一份{action}，根据用户要求进行修改

## 要求
1. 所有修改都基于***范本***。
2. 修改方向严格遵循***用户输入***。

## 响应格式
范本每行格式为：行号.范本内容

以下举例说明，假设范本内容如下：
1.第一行范本内容。
2.第二行范本内容。
3.第三行范本内容。
4.第四行范本内容。

### 修改
修改行，输出行号数字.mod.新修改的内容，如修改范本第一行时输出：
1.mod.修改后的第一行内容

### 增加
添加行，输出行号数字.add.后接新增内容，如在范本第二行新增内容时输出：
2.add.新增内容

### 删除
删除行，输出行号数字.del.，如删除第五行时输出：
5.del.
"""

###########################################

FIRST_TEMPLATE_PROMPT_DICT = {
    "WriteSynopsis": SYNOPSIS_FIRST_TEMPLATE,
    "DesignCharacters": CHARACTER_FIRST_TEMPLATE,
    "WriteOutline": OUTLINE_FIRST_TEMPLATE,
    "WriteChapters":CHAPTERS_FIRST_TEMPLATE
}

CN_ACTION= {
    "WriteSynopsis": "小说总纲",
    "DesignCharacters":"小说人物背景设计",
    "WriteOutline":"章节大纲",
    "WriteChapters":"小说章节内容"
}

###########################################

USER_INPUT_TEMPLATE = """
# 用户输入
{user_input}
"""

OUTLINE_TEMPLATE = """
# 本章大纲
{outline}
"""

CACHE_TEMPLATE = """
# 范本
{cache}

"""

###########################################

class NovelBaseContext(BaseContext):
    """小说创作的上下文"""
    novel_synopsis: Optional[dict] = None  # 总纲
    novel_background_entities: Optional[List[dict]] = None  # 实体设定
    novel_outline: Optional[List[str]] = None  # 前面章节大纲
    outline_cache: Optional[Union[dict, str]] = None  # 本章大纲缓存
    extracted_entities: dict = Field(default_factory=dict)  # 提取出的实体字典
    requirement: str = Field(default="")  # 用户输入 
    cache: Union[dict, str] = None # 缓存
    status: Status = Status.FIRST


class NovelBaseAction(Action):
    name: str = "base"
    i_context: NovelBaseContext = Field(default_factory=NovelBaseContext)
    input_args: Optional[BaseModel] = Field(default=None, exclude=True)
    
    async def run(self, *args, **kwargs) -> Message:
        """运行动作"""
        logger.info(f"Action: ...{self.__class__}...")
        
        prompt = await self._prompt_concat()
        content = await self._aask(prompt)
        # content = CH
        return Message(
            content=content,
            role = 'assistant',
            cause_by=self.__class__
        )
    
    async def _prompt_concat(self) -> str:
        """拼接提示词"""
        cls_name = self.__class__.__name__
        context = self.i_context

        if context.cache:
            logger.info(context.cache)
        prompt = ""

        if context.status == Status.FIRST:
            # 初次创作加载小说背景
            if context.novel_synopsis:
                prompt += SYNOPSIS_CONDITION_TEMPLATE.format(synopsis=context.novel_synopsis)

            if context.novel_outline:
                prompt += OUTLINE_CONDITION_TEMPLATE.format(previous_outlines=context.novel_outline)

            if context.extracted_entities:
                prompt += BACKGROUND_CONDITION_TEMPLATE.format(background_settings=context.extracted_entities)
            elif context.novel_background_entities:
                prompt += BACKGROUND_CONDITION_TEMPLATE.format(background_settings=context.novel_background_entities)
        elif context.status == Status.FIX:
            prompt += CACHE_TEMPLATE.format(cache=context.cache)

        if context.outline_cache:
            prompt += OUTLINE_TEMPLATE.format(outline=context.outline_cache)

        if context.requirement:
            prompt += USER_INPUT_TEMPLATE.format(user_input=context.requirement)
        
        if context.status == Status.FIRST:
            prompt += FIRST_TEMPLATE_PROMPT_DICT[cls_name]
        elif context.status == Status.FIX:
            prompt += FIX_TEMPLATE.format(action=CN_ACTION[cls_name])

        return prompt


class WriteSynopsis(NovelBaseAction):
    """写小说总纲"""
    name: str = "WriteSynopsis"

class DesignCharacters(NovelBaseAction):
    """设计小说人物"""
    name: str = "DesignCharacters"

class WriteOutline(NovelBaseAction):
    """写小说章节大纲"""
    name: str = "WriteOutline"

class WriteChapters(NovelBaseAction):
    """写小说章节内容"""
    name: str = "WriteChapters"



