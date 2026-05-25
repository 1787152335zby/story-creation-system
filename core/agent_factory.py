from typing import Optional
from llm.client import LLMClient


def snake_to_pascal(snake_name: str) -> str:
    """将 snake_case 转换为 PascalCase"""
    return "".join(word.capitalize() for word in snake_name.split("_"))


def create_agent(agent_name: str, llm_client: Optional[LLMClient] = None):
    """根据 agent 名称创建 Agent 实例
    
    Args:
        agent_name: Agent 名称，如 'outline_designer', 'plot_expander'
        llm_client: 可选的 LLM 客户端，如果为 None 则自动创建
        
    Returns:
        Agent 实例
        
    Example:
        agent = create_agent('outline_designer')
        agent = create_agent('plot_expander', llm_client)
    """
    import importlib
    
    module = importlib.import_module(f"agents.{agent_name}")
    class_name = snake_to_pascal(agent_name)
    agent_class = getattr(module, class_name)
    
    if llm_client:
        return agent_class(llm_client)
    return agent_class()


def get_agent_class(agent_name: str):
    """获取 Agent 类（不实例化）
    
    Args:
        agent_name: Agent 名称
        
    Returns:
        Agent 类
    """
    import importlib
    
    module = importlib.import_module(f"agents.{agent_name}")
    class_name = snake_to_pascal(agent_name)
    return getattr(module, class_name)
