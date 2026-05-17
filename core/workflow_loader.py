import yaml
from pathlib import Path
from typing import List, Dict, Optional


class WorkflowPhase:
    def __init__(self, data: Dict):
        self.name: str = data["name"]
        self.agent: str = data["agent"]
        self.output: str = data["output"]
        self.auto_skip: bool = data.get("auto_skip", False)
        self.split: bool = data.get("split", False)
        raw_condition = data.get("condition", True)
        if isinstance(raw_condition, bool):
            self.condition = "true" if raw_condition else "false"
        else:
            self.condition = str(raw_condition)

    def should_run(self, story_type_id: str) -> bool:
        if self.condition == "true":
            return True
        if self.condition == "false":
            return False
        if "story_type in" in self.condition:
            import ast
            allowed = ast.literal_eval(self.condition.split("[")[1].split("]")[0])
            return story_type_id in allowed
        return True


class WorkflowLoader:
    @staticmethod
    def load(path: Optional[Path] = None) -> List[WorkflowPhase]:
        if path is None:
            path = Path(__file__).resolve().parent.parent / "workflow.yaml"
        if not path.exists():
            raise FileNotFoundError(f"工作流配置不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return [WorkflowPhase(p) for p in data["phases"]]
