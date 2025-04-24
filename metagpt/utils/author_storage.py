import datetime
import json
import pandas as pd
from pathlib import Path

from typing import List, Dict, Optional, Any, Set, Tuple, Union
from pydantic import BaseModel, Field

"""
@Time    : 2025/4
@Author  : cursor
@File    : author_storage.py

JSON版简单rag
"""

class ShortOutline(BaseModel):
    """用于存储小说章节大纲的简短信息"""
    title: str
    abstract: str
    entity: List[str]
    update_time: Union[str, List]

class ShortBackground(BaseModel):
    """用于存储和管理作者小说相关的背景设定"""
    name: List[str]
    summary: List[str]
    tags: List[str]
    update_time: Union[str, List]

def dict_to_short_background(data: dict) -> ShortBackground:
    """
    将字典转换为ShortBackground对象
    data: {
        "persons": [{"name": "某人物名", "summary": "一句话总结"}],
        "locations": [{"name": "某地点", "summary": "一句话总结"}], 
        "organizations": [{"name": "某组织名", "summary": "一句话总结"}],
        "items": [{"name": "某物品名", "summary": "一句话总结"}]
    }
    
    """
    if "entities" in data:
        data = data['entities']
    name, summary, tags = [], [], []
    for tag in ('persons', 'locations', 'organizations', 'items'):
        if tag in data:
            for item in data[tag]:
                name.append(item['name'])
                summary.append(item['summary'])
                tags.append(tag)
    t = datetime.datetime.now().strftime("%Y%m%d%H%M")
    update_time = [t] * len(name)
    return ShortBackground(name=name, summary=summary, tags=tags, update_time=update_time)

# 定义JSON数据的键名
CHAPTER_KEYS = ['id', 'title', 'abstract', 'entity', 'update_time']
BG_ENTITY_KEYS = ['id', 'name', 'summary', 'update_time', 'tags']


class NovelOutline(BaseModel):
    """用于存储和管理小说章节大纲"""
    outlines: Dict[str, List[dict]] = Field(default_factory=dict)
    outline_file: Optional[Path] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, storage_path: str = "./test_workspace"):
        """初始化大纲存储"""
        super().__init__()

        path = Path(storage_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            
        if path.is_dir():
            self.outline_file = path / "outline.json"
        elif path.suffix == '.json':
            self.outline_file = path
        else:
            raise ValueError("storage_path必须是目录或.json文件")
            
        self._load_outlines()
        
    def _load_outlines(self):
        """从文件加载大纲"""
        if self.outline_file.exists():
            with open(self.outline_file, 'r', encoding='utf-8') as f:
                # 将数据转换为字典格式
                self.outlines = {
                    'columns': CHAPTER_KEYS,
                    'data': json.load(f)
                }
        else:
            # 初始化时使用CHAPTER_KEYS作为字段
            self.outlines = {
                'columns': CHAPTER_KEYS,
                'data': []
            }
            self.save_outlines()
            
    def save_outlines(self):
        """保存大纲到文件"""
        try:
            # 将数据转换为列表格式存储
            data = self.outlines['data']
            with open(self.outline_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存大纲出错: {e}")
            
    def add_outline(self, outline: ShortOutline) -> bool:
        """添加新的章节大纲"""
        try:
            new_idx = len(self.outlines['data']) + 1
            new_outline = dict(zip(self.outlines['columns'], [
                new_idx,
                outline.title,
                outline.abstract,
                outline.entity,
                datetime.datetime.now().strftime("%Y%m%d%H%M")
            ]))
            self.outlines['data'].append(new_outline)
            self.save_outlines()
            return True
        except Exception as e:
            print(f"添加大纲失败: {e}")
            return False
            
    def query_outline(self, outline_id: int = None, title: str = None) -> Optional[dict]:
        """查询章节大纲"""
        if outline_id is not None:
            return next((outline for outline in self.outlines['data'] if outline['id'] == outline_id), None)
        elif title is not None:
            return next((outline for outline in self.outlines['data'] if outline['title'] == title), None)
        return None
    
    def get_outline(self, last_k: int = 3) -> Optional[Tuple[List[dict], List[List[str]]]]:
        """获取最近K个章节大纲，仅返回id、title和abstract三项"""
        data = self.outlines['data']
        if not data:
            return None, None
        # 获取最近K条数据，并只保留需要的字段
        recent_data = data[-min(last_k, len(data)):]
        return [{'id': item['id'], 'title': item['title'], 'abstract': item['abstract']} for item in recent_data], \
                [item['entity'] for item in recent_data]
        
    def delete_outline(self, outline_id: int) -> bool:
        """删除章节大纲"""
        try:
            self.outlines['data'] = [outline for outline in self.outlines['data'] if outline['id'] != outline_id]
            self.save_outlines()
            return True
        except Exception as e:
            print(f"删除大纲失败: {e}")
            return False


class NovelBackground(BaseModel):
    """用于存储和管理作者小说相关的基础设定"""
    backgrounds: List[dict] = Field(default_factory=list)
    background_file: Optional[Path] = None
    
    class Config:
        arbitrary_types_allowed = True

    def __init__(self, storage_path: str = "./test_workspace"):
        """初始化背景设定存储"""
        super().__init__()

        path = Path(storage_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        if path.is_dir():
            self.background_file = path / "background.json"
        elif path.suffix == '.json':
            self.background_file = path
        else:
            raise ValueError("storage_path必须是目录或.json文件")
        self._load_backgrounds()

    def _load_backgrounds(self):
        """从文件加载背景设定"""
        if self.background_file.exists():
            with open(self.background_file, 'r', encoding='utf-8') as f:
                # 将数据转换为字典格式
                self.backgrounds = json.load(f)
        else:
            self.backgrounds = []
            self.save_backgrounds()


    def save_backgrounds(self):
        """保存背景设定到文件"""
        try:
            # 将数据转换为列表格式存储
            data = self.backgrounds
            with open(self.background_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存背景设定出错: {e}")

    def _add_background(self, name: str, summary: str, tags: str, update_time: str) -> int:
        """添加新的背景设定"""
        existing_background = [bg for bg in self.backgrounds if bg['name'] == name]
        if len(existing_background) == 0:
            background_id = len(self.backgrounds) + 1
            new_background = dict(zip(BG_ENTITY_KEYS, [
                background_id,
                name,
                [summary],
                [update_time],
                tags
            ]))
            self.backgrounds.append(new_background)
        elif len(existing_background) == 1:
            bg = existing_background[0]
            bg['summary'].append(summary)
            bg['update_time'].append(update_time)
            background_id = bg['id']
        else:
            raise Exception(f"发现多个同名背景设定: '{name}'")
        return background_id

    def add_backgrounds(self, short_background: ShortBackground):
        """添加新的背景设定"""
        name = short_background.name
        summary = short_background.summary
        tags = short_background.tags
        if not short_background.update_time:
            update_times = [datetime.datetime.now().strftime("%Y%m%d%H%M")] * len(name)
        elif not isinstance(short_background.update_time, list):
            update_times = [short_background.update_time] * len(name)
        else:
            update_times = short_background.update_time

        for i in range(len(name)):
            self._add_background(name[i], summary[i], tags[i], update_times[i])
        self.save_backgrounds()

    def delete_background(self, name: str) -> bool:
        """删除指定名称的背景设定"""
        if len([bg for bg in self.backgrounds if bg['name'] == name]) > 1:
            raise ValueError(f"发现多个同名背景设定: '{name}'。'name'应该是唯一键。")
        initial_len = len(self.backgrounds)
        self.backgrounds = [bg for bg in self.backgrounds if bg['name'] != name]
        if len(self.backgrounds) < initial_len:
            self.save_backgrounds()
            return True
        return False

    def search_backgrounds(self, names: List[str] = None) -> List[dict]:
        """搜索背景设定"""
        if names is None:
            return [{'name': bg['name'], 'summary': ''.join(map(str, bg['summary'])), 'tags': bg['tags']} 
                   for bg in self.backgrounds]
        else:
            return [{'name': bg['name'], 'summary': ''.join(map(str, bg['summary'])), 'tags': bg['tags']} 
                   for bg in self.backgrounds if bg['name'] in names]

    def rollback_backgrounds(self, time: str):
        """回滚背景设定"""
        def filter_items(summary, update_time):
            if not update_time:
                return summary, update_time
            if update_time[-1] <= time:
                return summary, update_time
                
            left, right = 0, len(update_time) - 1
            while left < right:
                mid = (left + right + 1) // 2
                if update_time[mid] <= time:
                    left = mid
                else:
                    right = mid - 1
                    
            if update_time[left] > time:
                return [], []
                
            return summary[:left+1], update_time[:left+1]

        for bg in self.backgrounds:
            bg['summary'], bg['update_time'] = filter_items(bg['summary'], bg['update_time'])
        self.save_backgrounds()

if __name__ == "__main__":
    # 初始化 AuthorNovelBackground 类
    background_manager = NovelBackground()

    # 创建短期背景设定对象
    short_background = ShortBackground(
        name=["北京", "上海", "张三"],
        summary=["关于北京的简介01", "关于上海的简介", "关于张三的简介"],
        tags=["城市", "城市", "人物"],
        update_time=datetime.datetime.now().strftime("%Y%m%d%H%M")
    )

    # 添加背景设定
    background_manager.add_backgrounds(short_background)

    # 等待一段时间
    import time
    time.sleep(1)

    # 创建新的短期背景设定对象
    new_short_background = ShortBackground(
        name=["广州", "北京"],
        summary=["关于广州的简介", "关于北京的简介02"],
        tags=["城市", "人物"],
        update_time=datetime.datetime.now().strftime("%Y%m%d%H%M")
    )

    # 添加新的背景设定
    background_manager.add_backgrounds(new_short_background)

    # 搜索背景设定
    search_result = background_manager.search_backgrounds(["北京", "广州", "张三"])
    print("Search Results:")
    print(search_result)

    # 删除背景设定
    background_name_to_delete = "广州"
    delete_success = background_manager.delete_background(background_name_to_delete)
    print(f"Delete Success: {delete_success}")

    # 初始化 NovelOutline 类
    outline_manager = NovelOutline()

    # 创建小说大纲对象
    novel_outline = ShortOutline(
        title='测试小说',
        abstract='这是一个测试小说的摘要',
        entity=['人物1', '地点1'],
        update_time=datetime.datetime.now().strftime("%Y%m%d%H%M")
    )

    # 添加小说大纲
    outline_manager.add_outline(novel_outline)

    # 等待一段时间
    time.sleep(1)

    # 创建新的大纲对象
    new_novel_outline = ShortOutline(
        title='测试小说2',
        abstract='这是一个测试小说的新摘要',
        entity=['人物2', '地点2'],
        update_time=datetime.datetime.now().strftime("%Y%m%d%H%M")
    )

    # 添加新的大纲
    outline_manager.add_outline(new_novel_outline)

    # 搜索大纲内容
    search_result, entity = outline_manager.get_outline(1)  # 获取第一个大纲
    print("Search Results:")
    print(search_result)
    print(entity)

    # 删除大纲
    delete_success = outline_manager.delete_outline(outline_id=1)  # 删除第一个大纲
    print(f"Delete Success: {delete_success}")


