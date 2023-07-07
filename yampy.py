from typing import Any, Dict, List, Tuple

_DEBUG: bool = True

PARENT: str = "par"
LEFT: str = "l"
RIGHT: str = "r"
SPACES: str = "sp"
SEP: str = "sep"
LIST: str = "lst"
SUB: str = "sub"
ITEM: str = "item"
ITEM_MARK: str = "- "
COLON: str = ":"
T: str = "true"
F: str = "false"


def obj(l_list: List[Dict[str, Any]], parent: int, lst: bool):
    out: Dict = {}
    o_list: List = []
    for i in range(len(l_list)):
        if l_list[i][PARENT] != parent:
            continue
        key: str = l_list[i][LEFT]
        if l_list[i][LIST]:
            ret = obj(l_list, i, True)
            if not isinstance(ret, list):
                ret = [ret]
            out[key] = ret
        elif l_list[i][SUB]:
            out[key] = obj(l_list, i, False)
            o_list = [out]
        elif l_list[i][ITEM] and not l_list[i][SEP]:
            o_list.append(key)
        elif l_list[i][ITEM]:
            res = {key: l_list[i][RIGHT]}
            res.update(obj(l_list, i, l_list[i][LIST]))
            o_list.append(res)
        else:
            out[key] = l_list[i][RIGHT]
    if lst:
        return o_list
    return out


def resolve(val: str) -> Any:
    if not val:
        return None
    ns_val = val.strip().lstrip("-+")
    if ns_val.isnumeric():
        return int(ns_val)
    try:
        tval = float(ns_val)
        return int(ns_val) if tval == int(ns_val) else float(ns_val)
    except (TypeError, ValueError):
        if ns_val.lower() == T:
            return True
        elif ns_val.lower() == F:
            return False
        elif ns_val.lower() == "null":
            return None
        else:
            return ns_val


def this_line(line: str) -> Dict[str, Any]:
    base: Dict = {LIST: False, SPACES: len(line) - len(line.lstrip(" ")), PARENT: -1}
    parts: Tuple[str, str, str] = line.strip().partition(COLON)
    if parts[2][0:1] != " " and len(parts[2]):
        base.update(
            {
                LEFT: line.strip()
                if line.strip()[0 : len(ITEM_MARK)] != ITEM_MARK
                else line.strip()[len(ITEM_MARK) :],
                SEP: False,
                RIGHT: "",
                ITEM: True if line.strip()[0 : len(ITEM_MARK)] == ITEM_MARK else False,
                SUB: False,
            }
        )
        return base
    right: Any = resolve(parts[2].strip())
    left: str = parts[0].strip()
    left = left if left[0 : len(ITEM_MARK)] != ITEM_MARK else left[len(ITEM_MARK) :]
    base.update(
        {
            LEFT: left,
            RIGHT: right,
            SEP: True if parts[1] else False,
            ITEM: True if parts[0][0 : len(ITEM_MARK)] == ITEM_MARK else False,
            SUB: True if right is None and parts[1] == COLON else False,
        }
    )
    return base


def skip(line: str):
    comment: str = "#"
    sep: str = "---"
    return (
        not len(line.strip())
        or line.strip()[0 : len(comment)] == comment
        or (len(line) > 2 and line[0 : len(sep)] == sep)
    )


def compute_parent(l_list: List[Dict[str, Any]], l: Dict[str, Any]) -> int:
    cnt: int = len(l_list)
    if not cnt or not l[SPACES]:
        return -1
    if l_list[cnt - 1][SPACES] == l[SPACES]:
        return l_list[cnt - 1][PARENT]
    elif l_list[cnt - 1][SPACES] < l[SPACES]:
        return cnt - 1
    elif l[SPACES] and l[PARENT] == -1:
        for p in range(cnt - 1, -1, -1):
            if l_list[p][SPACES] == l[SPACES]:
                return l_list[p][PARENT]


def parse_lines(lines: List[str]) -> Dict[str, Any]:
    line: str = ""
    cnt: int = 0
    l_list: List[Dict[str, Any]] = []
    if not len(lines):
        return {}
    for line in lines:
        if skip(line):
            continue
        l = this_line(line)
        l[PARENT] = compute_parent(l_list, l)
        if cnt and l[ITEM] and l[SPACES] > l_list[cnt - 1][SPACES]:
            l_list[cnt - 1][LIST] = True
        l_list.append(l)
        cnt += 1
    del lines
    if not len(l_list):
        return {}
    if _DEBUG:
        for i, o in enumerate(l_list):
            print(i, o)
    final = obj(l_list, -1, l_list[0][ITEM])
    if _DEBUG:
        print(final)
    return final


def render(data: Any, depth: int = 0, lst: bool = False) -> str:
    out: str = ""
    start: str = "  " * depth
    dash: str = ITEM_MARK if lst else ""
    if isinstance(data, list):
        for i in data:
            out += render(i, depth, True)
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) or isinstance(v, list):
                out += f"{start}{dash}{k}:\n" + render(v, depth + 1)
            else:
                if isinstance(v, bool):
                    v = T if v else F
                out += f"{start}{dash}{k}: {v}\n"
                dash = "  " if dash == ITEM_MARK else ""
    else:
        out += f"{start}{dash}{data}\n"
    return out


def parse(raw) -> Dict[str, Any]:
    return parse_lines(raw.replace("\n", "\r").split("\r"))
