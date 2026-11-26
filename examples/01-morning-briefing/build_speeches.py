def build_speeches(payload: dict) -> list:
    items = sorted(payload["schedule_list"], key=lambda x: x["begin_time"])
    out = [f"早上好，你今天共有 {len(items)} 项安排，下面开始播报"] if items else ["今天没有日程安排"]
    for i, it in enumerate(items, 1):
        s = f"第{i}项，{it['subject']}，时间{speak_time(it['begin_time'])}"
        if it.get("creator_name"):
            s += f"，由{it['creator_name']}发起"
        if it.get("meeting"):
            s += "，这是一场会议"
        if it.get("description"):
            s += f"，主要议题是{it['description']}"
        names = [a.get("name") for a in it.get("attendees", []) if a.get("name")]
        if names:
            s += "，参加的主要人员有" + "、".join(names)
        out.append(s)
    out.append("今天日程就是这些，我先回去充电了。")
    return out
