#!/usr/bin/env python
"""
@Time    : 2025/3
@Author  : cursor
@File    : author.py
"""
import datetime
import itertools
import json
from datetime import time
from pathlib import Path
from colorama import Fore, Style, Back
from typing import List, Optional, Tuple, Union, Dict
from pydantic import Field, BaseModel

from metagpt.actions.action import Action
from metagpt.actions.add_requirement import UserRequirement
from metagpt.actions.author_actions import DesignCharacters, NovelBaseContext, WriteChapters, WriteOutline, WriteSynopsis, Status
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.roles.critic import Review
from metagpt.roles.role import RoleReactMode
from metagpt.schema import Message
from metagpt.utils.author_storage import NovelOutline, NovelBackground, ShortBackground, ShortOutline, dict_to_short_background
from metagpt.utils.repair_llm_raw_output import extract_state_value_from_output

IS_SATISFIED_TEMPLATE = """
### 任务说明
你需要根据用户的反馈内容，精确判断其对之前生成的内容是否满意。请特别注意用户表达中的情感倾向、修改请求和明确评价。

### 判断标准
【YES】当用户出现以下情况时：
- 明确表示肯定
- 给予正面评价

【NO】当用户出现以下情况时：
- 明确表示否定
- 指出具体问题或错误
- 要求修改内容
- 表达失望或不满情绪

### 用户输入
{context}

### 输出要求
1. 除"YES"或"NO"外，不含其他文字
2. 无法明确判断时（如中性反馈），默认输出"NO"

### 输出示例
示例1：
用户说："这个版本很好，就用这个了"
YES

示例2：
用户说："修改一下，这段剧情中主角应该表现得更果断"
NO
"""

LLM_REACT_TEMPLATE = """
# 任务
根据**用户输入**，准确判断其意图并选择最匹配的响应动作。

## 可用动作类别
0. 【写小说总纲】- 当用户提供小说基本构思、题材想法或要求整体框架时选择
   - 示例："帮我构思一个科幻小说的整体框架"、"我想写一部都市爱情小说，请给出大纲"
   
1. 【设计人物】- 当用户提供人物基本要求或要求创建角色时选择
   - 示例："为我的侦探小说设计一个主角"、"需要创建一个反派角色，性格阴险狡诈"
   
2. 【写章节大纲】- 当用户要求基于已有剧情继续发展新章节时选择
   - 示例："根据前三章剧情，请写出第四章大纲"、"接着上一章结尾，发展新的情节"
   
3. 【扩写章节，自带章节大纲】- 当用户提供具体章节大纲，要求根据输入的大纲详细扩写时选择
   - 示例："请将以下章节大纲扩写成完整章节：[大纲内容]"

4. 【扩写章节，无章节大纲】- 当用户仅要求扩写章节，但输入中不包含章节大纲时选择
   - 示例："请将存储的最新章节大纲扩写成完整章节"
   
5. 【其他意图】- 当输入明显不属于以上4种类别时选择

## 用户输入
{text}

## 输出要求
单独一行输出对应的数字编号（1-5）
"""

NER_SUMMARY_PROMPT = """
# 实体识别与总结任务
根据**用户输入**，识别输入文本中的实体，并附带一句话总结。

## 任务说明
请从**用户输入**中准确识别并分类以下实体类型：
1. 人名：人物角色名称，注意区分昵称
2. 地点：具有特殊意义或唯一性的地理名称/地点（如有名称的山、市集、城市等，没有命名的地点不识别）
3. 组织：具有唯一性的机构/团体等组织名称
4. 物品：具有特殊意义或重要性的物品（如神器、法宝等，普通生活用品不识别）

## 处理要求
1. 对每个识别出的实体，需要提供：
   - 标准化名称（消除指代歧义）
   - 一句话简单总结
2. 最后需提供整个文本的概括性总结

## 用户输入
{text}

## 输出规范
只能输出以下JSON格式，确保以下字段完整，结构正确：
{
    "entities": {
        "persons": [
            {
                "name": "实体全称/标准名称",
                "summary": "总结该人物的特点和行为"
            }
        ],
        "locations": [
            {
                "name": "规范地点名称",
                "summary": "总结该地点在文中的特点"
            }
        ],
        "organizations": [
            {
                "name": "组织正式名称",
                "summary": "说明该组织的性质或作用"
            }
        ],
        "items": [
            {
                "name": "物品标准名称",
                "summary": "说明该物品的功能"
            }
        ]
    },
    "text_summary": "用20-30字概括文本核心内容，包含主要实体和关键事件"
}
"""


## hyperparams
OUTLINE_K = 3 # 使用最近K个章节大纲

def extract_json_from_str(text: str) -> Optional[dict]:
    """从字符串中提取JSON内容并解析

    Args:
        text (str): 包含JSON的字符串

    Returns:
        Optional[dict]: 解析后的JSON字典，解析失败返回None
    """
    try:
        # 首先尝试直接解析整个字符串
        try:
            return json.loads(text)
        except:
            pass
            
        # 查找json'''标记的内容
        start = text.find("json'''")
        if start != -1:
            start += 7
            end = text.find("'''", start)
            if end != -1:
                text = text[start:end]
                
        # 查找{开始的第一个完整JSON
        start = text.find("{")
        if start != -1:
            stack = []
            end = -1
            for i in range(start, len(text)):
                if text[i] == "{":
                    stack.append("{")
                elif text[i] == "}":
                    if not stack:  # 防止出现多余的}导致stack为空时继续pop
                        break
                    stack.pop()
                    if not stack:
                        end = i
                        break
            
            if end != -1:  # 只有找到匹配的}才进行切片
                text = text[start:end+1]
                        
        # 清理和标准化JSON字符串
        text = text.strip()
        text = text.replace("'", '"')
        text = text.replace('\n', ' ')
        
        # 尝试解析JSON
        return json.loads(text)
        
    except (json.JSONDecodeError, AttributeError, IndexError):
        return None


class Author(Role):
    """
    作者角色，负责小说创作的全流程管理

    属性:
        name (str): 'author'
        profile (str): '作家'
        goal (str): 创作目标，包括小说质量要求
        constraints (str): 创作约束条件，确保小说质量

        working_dir (str): 工作目录路径
        synopsis_file (Path): 小说总纲文件路径

        synopsis (str): 持久化的小说总纲
        outline (NovelOutline): 持久化的小说大纲
        background (NovelBackground): 持久化的背景知识库
        status (Status): 当前创作状态， Enum（FIRST, FIX, FINISHED）
            示例：Status.FIRST
        cache (Union[dict, str]): 临时缓存中间结果
            示例：{"chapter1": "第一章内容..."}

        reviwer (Action): 审核动作对象，用于质量控制和修改建议
            示例：Review()
        last_action (str): 最近执行的动作名称
            示例："WriteSynopsis"
    """

    name: str = "author"
    profile: str = "作家"
    goal: str = "创作引人入胜、富有创意且结构完整的小说"
    constraints: str = (
        "小说应该具有引人入胜的角色、连贯的情节和吸引人的叙事。"
        "遵循标准的写作规范并保持一致的写作风格"
    )

    working_dir: str = None
    synopsis_file: Path = None

    reviwer: Action = Review
    last_action: str = None

    synopsis: str = None
    outline: NovelOutline = Field(default_factory=NovelOutline)
    background: NovelBackground = Field(default_factory=NovelBackground)
    
    status: Status = Status.FIRST
    cache: Union[dict, str] = None
    outline_cache: Optional[dict] = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([WriteSynopsis, DesignCharacters, WriteOutline, WriteChapters])
        self._set_react_mode(RoleReactMode.REACT.value)
        self._watch([UserRequirement, self.reviwer]) # human or other agent
        self._load_workspace()

    def _load_workspace(self) -> None:
        """从工作目录加载已有文件"""
        try:
            if not self.working_dir:
                self.working_dir = Path("novel/novel_" + str(int(time.time())))
            
            work_dir = Path(self.working_dir)
            work_dir.mkdir(parents=True, exist_ok=True)

            # 加载小说总纲
            synopsis_file = next(work_dir.glob("*synopsis*.txt"), work_dir / "synopsis.txt")
            if not synopsis_file.exists():
                synopsis_file.touch()
                self.synopsis = ""
            else:
                with open(synopsis_file, 'r', encoding='utf-8') as f:
                    self.synopsis = f.read()

            # 加载小说大纲
            outline_file = next(work_dir.glob("*outline*.json"), work_dir)
            self.outline = NovelOutline(storage_path=str(outline_file))


            # 加载背景知识
            bg_file = next(work_dir.glob("*background*.json"), work_dir)
            self.background = NovelBackground(storage_path=str(bg_file))

            self.synopsis_file = synopsis_file

        except Exception as e:
            logger.warning(f"工作目录文件加载失败: {str(e)}")


    async def _act(self) -> Message | None:
        """执行当前待办任务"""
        if self.rc.todo is None:
            return None
        
        logger.debug(f"执行动作: {self.rc.todo}")
        msg = await self.rc.todo.run()

        self.last_action = self.rc.todo.__class__
        
        if self.status == Status.FIRST:
            self.cache = msg.content
        else:
            self.cache, mod_log = Author.modify_changes(self.cache, msg.content)
            msg.content = mod_log
        self.rc.memory.add(msg)
        return msg

    async def _ner_and_summary(self, input: str):
        prompt = NER_SUMMARY_PROMPT.replace("{text}", input) # json & format
        rsp = await self.llm.aask(msg=prompt, stream=False)
        logger.info(f"实体识别与总结: {rsp}")
        try:
            json_rsp = extract_json_from_str(rsp)
            return json_rsp
        except Exception as e:
            logger.error(f"实体识别与总结失败: {str(e)}")
            return None

    async def _is_satisfied(self, context: str):
        """检查是否满意当前内容"""
        if "OK" in context.upper():
            self.status = Status.FINISHED
        else:
            # prompt = IS_SATISFIED_TEMPLATE.format(context=context)
            # rsp = await self.llm.aask(msg=prompt, stream=False)
            # logger.info(f"检查是否满意当前内容: {rsp}")
            # self.status = Status.FINISHED if "YES" in rsp.upper() else Status.FIX

            self.status = Status.FIX
            
    async def _llm_react_think(self, text: str) -> int:
        """根据用户输入判断下一步动作"""
        prompt = LLM_REACT_TEMPLATE.format(text=text)
        next_state = await self.llm.aask(prompt)
        next_state = extract_state_value_from_output(next_state)
        logger.info(f"LLM判断用户意图state: {next_state}， (0: WriteSynopsis, 1: DesignCharacters, 2: WriteOutline, 3: WriteChapters using input, 4: WriteChapters using outline, 5: other)")
        
        if not next_state.isdigit():
            logger.error(f"意图state返回错误, {next_state}, todo will be set to None")
            return -1
        return int(next_state)
        # return 4

    async def _think(self) -> bool:
        """根据当前状态和消息确定下一个动作"""
        if not self.rc.news:
            return False
            
        msg = self.rc.news[0]
        logger.info(f"_think msg: {msg}")

        if "quit" in msg.content.lower() or "退出" in msg.content:
            await self._finish_and_save()
            return False

        if not hasattr(self, 'last_action') or not self.last_action:
            state = await self._llm_react_think(msg.content)  
            await self._prepare_context(state, msg)
            return bool(self.rc.todo)
        
        await self._is_satisfied(msg.content)

        if self.status == Status.FINISHED: # 结束
            await self._finish_and_save()
        elif self.status == Status.FIX: # 重复上一动作
            await self._prepare_context(self.last_action, msg)
        return bool(self.rc.todo)


    async def _prepare_context(self, todo: Union[Action, int], msg: Message):
        using_outline = False
        if isinstance(todo, int) and todo in range(len(self.actions) + 1):
            if todo == -1:
                logger.error(f"意图state返回错误, {todo}, todo will be set to None")
                self.rc.todo = None
                return
            elif todo == 4:
                using_outline = True
                todo = 3
            todo = self.actions[todo].__class__

        context = NovelBaseContext(
            requirement=msg.content,
            status=self.status,
        )

        if self.status == Status.FIX:
            cache = self.cache
            if isinstance(cache, str):
                cache = cache.split('\n')

            idx_cache = ""
            for idx, line in zip(range(len(cache)), cache):
                idx_cache += f"{idx}.{line}\n"
            context.cache = idx_cache

        if todo == WriteSynopsis:
            """准备撰写总纲"""
            if len(self.synopsis) > 10 and self.status == Status.FIRST:
                logger.error(f"总纲已经存在于{self.synopsis_file},重写会影响已经创作的内容。请在干净工作目录重写。")
                self.rc.todo = None
                return
   
            self.rc.todo = WriteSynopsis(i_context=context)

        elif todo == DesignCharacters:
            """准备设计人物"""
            if len(self.synopsis) < 10:
                logger.error("设计人物需要先设计总纲。")
                self.rc.todo = None
                return
                
            context.novel_synopsis = self.synopsis
            context.novel_outline = self.outline.get_outline(OUTLINE_K)
            context.novel_background_entities = self.background.search_backgrounds() # todo
            self.rc.todo = DesignCharacters(i_context=context)

        elif todo == WriteOutline:
            """准备撰写大纲"""
            context.novel_synopsis = self.synopsis
            context.novel_outline, _ = self.outline.get_outline(OUTLINE_K)
            context.novel_background_entities = self.background.search_backgrounds()
            self.rc.todo = WriteOutline(i_context=context)

        elif todo == WriteChapters:
            """准备撰写章节"""
            context.novel_synopsis = self.synopsis

            if self.status == Status.FIRST:
                if using_outline:
                    outline, entity_name_list = self.outline.get_outline(1) 
                    entity_name = list(itertools.chain.from_iterable(entity_name_list))
                    
                else:
                    outline = msg.content
                    entity = await self._ner_and_summary(outline) 
                    entity_name = dict_to_short_background(entity)
                    self.outline_cache = {'outline': outline, 'entity_name': entity_name}
                context.outline_cache = outline
                context.extracted_entities = self.background.search_backgrounds(entity_name)
            self.rc.todo = WriteChapters(i_context=context)

        else:
            logger.error(f"无法识别的意图: {todo}") 
            self.rc.todo = None
        return


    @staticmethod
    def modify_changes(original: Union[List[str], str], cache: Union[List[str], str]) -> Tuple[str, str]:
        def green(s: str) -> str:
            return Back.GREEN + s + Style.RESET_ALL
        
        def red(s: str) -> str:
            return Back.RED + s + Style.RESET_ALL
        
        def yellow(s: str) -> str:
            return Back.YELLOW + s + Style.RESET_ALL

        if isinstance(original, str):
            original_lines = original.splitlines()
        else:
            original_lines = original

        if isinstance(cache, str):
            cache_lines = cache.splitlines()
        else:
            cache_lines = cache
        
        # 解析所有指令并排序 (1-based)
        instructions = []
        for line in cache_lines:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split('.', 2)
            if len(parts) < 3:
                continue
                
            line_num_str, op, content  = list(map(lambda x: x.strip(), parts))
            if not line_num_str.isdigit():
                continue
                
            if op in ('mod', 'add', 'del'):
                instructions.append((
                    int(line_num_str), 
                    op, 
                    content if content else None
                ))
        
        # 按行号升序排序
        instructions.sort(key=lambda x: x[0])
        
        # 初始化双指针和结果列表
        orig_index = 0
        cache_index = 0
        result, modify_log = [], []

        while orig_index < len(original_lines) or cache_index < len(instructions):
            orig_number = orig_index + 1

            if cache_index >= len(instructions):
                # 如果缓存已处理完，直接将剩余的原始行加入结果
                result.extend(original_lines[orig_index:])
                modify_log.extend(
                    list(map(lambda x: f"{x[0]+orig_number}:org {x[1]}", enumerate(original_lines[orig_index:])))    
                )
                break

            if orig_index >= len(original_lines):
                # 如果原始行已处理完，处理剩余的缓存指令
                while cache_index < len(instructions):
                    line_num, op, content = instructions[cache_index]
                    if op == 'add':
                        result.append(content)
                        modify_log.append( green(f'{line_num}:add {content}') )
                    cache_index += 1
                break

            # 获取当前原始行和缓存指令
            current_line = original_lines[orig_index]
            line_num, op, content = instructions[cache_index]
            
            if line_num > orig_number:
                # 缓存指令的行号大于当前原始行号，直接添加原始行
                result.append(current_line)
                modify_log.append(f'{orig_number}:org {current_line}')
                orig_index += 1
            elif line_num == orig_number:
                # 缓存指令的行号等于当前原始行号，根据指令操作
                if op == 'mod':
                    result.append(content)
                    
                    modify_log.append(f'{orig_number}:org {current_line}')
                    modify_log.append( yellow(f'{line_num}:mod {content}' + Style.RESET_ALL) )
                elif op == 'add':
                    result.append(content)
                    result.append(current_line)

                    modify_log.append( green(f'{line_num}:add {content}' + Style.RESET_ALL) )
                    modify_log.append(f'{orig_number}:org {current_line}')
                elif op == 'del':
                    # 删除操作，不添加当前行
                    modify_log.append( red(f'{line_num}:del {current_line}' + Style.RESET_ALL) )


                orig_index += 1
                cache_index += 1
            else:
                # 缓存指令的行号小于当前原始行号，跳过无效指令
                if op == 'add':
                    result.append(content)
                modify_log.append( green(f'{line_num}:add {content}' + Style.RESET_ALL) )
                cache_index += 1

        return '\n'.join(result), '\n'.join(modify_log)


    async def _save_to_database(self):
        """将信息存储到对应的数据结构中"""
        action = self.last_action
        cache = self.cache

        if cache is None:
            logger.info("没有缓存信息，跳过存储。")
            return

        # 根据最后执行的动作进行相应的存储操作
        if action == WriteSynopsis:
            self.synopsis = cache

            self.synopsis_file.write_text(
                str(self.synopsis), 
                encoding="utf-8"
            )
        
        elif action == DesignCharacters:
            entity = await self._ner_and_summary(cache) # todo
            bg = dict_to_short_background(entity)
            self.background.add_backgrounds(bg)
        
        elif action == WriteOutline:
            entity = await self._ner_and_summary(cache)
            bg: ShortBackground = dict_to_short_background(entity)

            outline = ShortOutline(
                title='test', # todo
                abstract=cache,
                entity=bg.name,
                update_time=datetime.datetime.now().strftime("%Y%m%d%H%M")
            )
 
            self.outline.add_outline(outline)
            self.background.add_backgrounds(bg)
        
        elif action == WriteChapters:
            t = datetime.datetime.now().strftime("%Y%m%d%H%M")
            if self.outline_cache:
                outline = ShortOutline(
                    title='test', # todo
                    abstract=self.outline_cache['outline'],
                    entity=self.outline_cache['entity_name'],
                    update_time=t
                )
                self.outline.add_outline(outline)
            save_path = self.synopsis_file.parent / f"chapter_{t}.txt" # 仅存储
            save_path.write_text(self.cache, encoding="utf-8")
        
        else:
            raise ValueError(f"未知动作: {action}")

    async def _finish_and_save(self):
        """结束创作, 存储信息"""
        await self._save_to_database()  
        self.rc.todo = None
        self.cache = None
        self.outline_cache = None
        self.status = Status.FINISHED
