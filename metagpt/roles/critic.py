from metagpt.actions.author_actions import DesignCharacters, WriteChapters, WriteOutline, WriteSynopsis
from metagpt.roles import Role
from metagpt.actions import Action
from metagpt.schema import Message

HUMAN_PROMPT_TEMPLATE = """
{sys_feedback}

1.对上述回答内容满意，回复"OK" -> 缓存，结束
2.不满意,回复修改意见 -> 迭代修改
"""

class Review(Action):
    """A human role that provides critiques and feedback on the author's work."""
    
    name: str = "Review"
    desc: str = "Review the author's work"
    
    async def run(self, sys_feedback: str):
        prompt = HUMAN_PROMPT_TEMPLATE.format(sys_feedback=sys_feedback)
        rsp = await self._aask(prompt)

        return Message(
            content=rsp,
            role = 'user',
            cause_by = self.__class__,
        )

class HumanCritic(Role):
    """A human role that provides critiques and feedback on the author's work."""
    
    name: str = "Human Critic"
    profile: str = "Human Critic"
    goal: str = "Provide constructive feedback on the author's work"
    constraints: str = "Be objective and professional in critiques"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([Review])
        self._watch([WriteSynopsis, DesignCharacters, WriteOutline, WriteChapters])
