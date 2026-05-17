import re


def _min_duration_for_shot(desc: str) -> float:
    min_dur = 2.0

    has_dialogue = bool(re.search(r'["""]', desc))
    has_speech_verb = bool(re.search(r'[说喊叫问答吼道骂嚷回应]', desc))
    if has_dialogue or has_speech_verb:
        min_dur = max(min_dur, 3.0)

    if re.search(r'缓慢\s*(推|拉|摇|移|跟)', desc):
        min_dur = max(min_dur, 4.0)

    if re.search(r'(斯坦尼康|长镜头|连续跟拍)', desc):
        min_dur = max(min_dur, 10.0)

    if re.search(r'(手持|抖动|晃动)', desc):
        min_dur = max(min_dur, 2.5)

    return min_dur


def validate_storyboard_durations(content: str) -> str:
    def fix_one(match):
        prefix = match.group(1)
        duration_str = match.group(2)
        rest = match.group(3)

        try:
            current = float(duration_str)
        except ValueError:
            return match.group(0)

        min_dur = _min_duration_for_shot(rest)
        adjusted = max(current, min_dur)

        if abs(adjusted - current) < 0.01:
            return match.group(0)

        new_dur = f"{adjusted:.1f}" if adjusted != int(adjusted) else f"{int(adjusted)}"
        return f"{prefix}{new_dur}s{rest}"

    pattern = r'(镜头\d+\s*\|\s*)([\d.]+)s([\s\S]*?)(?=\n\s*→\s*(?:镜头|下一场|状态))'
    result = re.sub(pattern, fix_one, content)
    return result
