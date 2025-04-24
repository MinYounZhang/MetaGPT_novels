#!/usr/bin/env python

import asyncio
from metagpt.roles.author import Author
from metagpt.roles.critic import HumanCritic
from metagpt.team import Team

content = [
    """
    我想写武侠小说,剧情是:主角生活边塞,意外卷入武林纷争,被隐世高人赏识,传授基础武功。
    为帮朋友复仇,踏足中原,破解阴谋,结识红颜,后奔赴西域,海外仙岛。
    最终一切揭晓,发现满是矛盾无奈,破解最终阴谋后隐居。
    将剧情补全为小说大纲,参考金庸小说,全书不少于100万字。
    """,
    "创作人物prompt",
    "章节大纲prompt",
    "将章节大纲扩写为2000字章节,突出惊悚氛围"
]

async def main():
    COST = 100
    MAX_EPOCH = 99

    # 初始化Author
    working_dir = "test_workspace"
    team = Team(use_mgx=False)
    team.hire([
        Author(working_dir=working_dir), 
        HumanCritic(is_human=True)
    ])

    # 初始化消息内容
    test_content = content[0]
    print(f"测试输入: {test_content}")
    team.invest(COST)
    team.run_project(test_content)

    print("测试Author完整工作流程...")
    result = await team.run(MAX_EPOCH)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
